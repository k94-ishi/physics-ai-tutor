import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import (
    concept_repository,
    embedding_repository,
    question_concept_repository,
    question_repository,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import QuestionResponse
from physics_ai_tutor.services.question_presentation_service import (
    prepare_for_response,
)
from physics_ai_tutor.services.response_language import (
    ResponseLanguage,
    TranslationNeeds,
)

logger = logging.getLogger(__name__)


@dataclass
class RelatedQuestions:
    items: list[QuestionResponse]
    # Rows and concept names a strict reader missed ([53]).
    needs: TranslationNeeds


# Kept as simple, named constants so the relative weighting of question vs.
# concept similarity can be tuned later without touching the algorithm.
QUESTION_SIMILARITY_WEIGHT = 0.7
CONCEPT_SIMILARITY_WEIGHT = 0.3

CANDIDATE_POOL_SIZE = 50


async def _embedding_neighbours(
    db: AsyncSession, question_id: int, lang: Language, exclude_statuses: list[str]
) -> tuple[dict[int, float], dict[int, Question]]:
    """Nearest questions by question embedding, within one language."""
    similarity: dict[int, float] = {}
    questions_by_id: dict[int, Question] = {}

    # Compare within one language; fall back to the row's original language
    # for rows that were never embedded in `lang`.
    search_language = lang.value
    source_embedding = await embedding_repository.get_embedding(
        db, question_id, "question", language=search_language
    )
    if source_embedding is None:
        source_question = await question_repository.get_question(db, question_id)
        if source_question is not None:
            search_language = source_question.original_language
            source_embedding = await embedding_repository.get_embedding(
                db, question_id, "question", language=search_language
            )
    if source_embedding is None:
        return similarity, questions_by_id

    rows = await embedding_repository.search_similar_embeddings(
        db,
        embedding=source_embedding,
        embedding_type="question",
        limit=CANDIDATE_POOL_SIZE,
        exclude_question_ids=[question_id],
        exclude_statuses=exclude_statuses,
        language=search_language,
    )
    for _, question, distance in rows:
        similarity[question.id] = 1 - distance
        questions_by_id[question.id] = question
    return similarity, questions_by_id


async def _concept_neighbours(
    db: AsyncSession, question_id: int
) -> tuple[list[int], set[int]]:
    """The source's concept ids and the questions sharing them.

    A RAG answer also brings the concepts of the QAs it was grounded in
    (`retrieved_question_ids`), with no extra search or LLM call.
    """
    source_question = await question_repository.get_question(db, question_id)
    reference_ids = source_question.retrieved_question_ids if source_question else []

    concept_ids = set(
        await question_concept_repository.get_concept_ids_for_question(db, question_id)
    )
    for reference_id in reference_ids:
        concept_ids.update(
            await question_concept_repository.get_concept_ids_for_question(
                db, reference_id
            )
        )

    sharing = set(
        await question_concept_repository.get_questions_sharing_concepts(
            db,
            question_id=question_id,
            exclude_ids=[question_id],
            limit=CANDIDATE_POOL_SIZE,
        )
    )
    for reference_id in reference_ids:
        sharing.update(
            await question_concept_repository.get_questions_sharing_concepts(
                db,
                question_id=reference_id,
                exclude_ids=[question_id, *reference_ids],
                limit=CANDIDATE_POOL_SIZE,
            )
        )
    return list(concept_ids), sharing


async def _load_missing(
    db: AsyncSession,
    candidate_ids: set[int],
    questions_by_id: dict[int, Question],
    exclude_statuses: list[str],
) -> None:
    """Load concept-only candidates that the embedding search did not return."""
    for candidate_id in candidate_ids:
        if candidate_id in questions_by_id:
            continue
        candidate = await question_repository.get_question(db, candidate_id)
        if candidate is not None and candidate.status not in exclude_statuses:
            questions_by_id[candidate_id] = candidate


def _score(
    candidate_ids: set[int],
    questions_by_id: dict[int, Question],
    question_similarity: dict[int, float],
    concept_similarity: dict[int, float],
) -> list[tuple[float, Question]]:
    """Weighted question + concept similarity, best first."""
    scored = []
    for candidate_id in candidate_ids:
        candidate = questions_by_id.get(candidate_id)
        if candidate is None:
            continue
        score = QUESTION_SIMILARITY_WEIGHT * question_similarity.get(
            candidate_id, 0.0
        ) + CONCEPT_SIMILARITY_WEIGHT * concept_similarity.get(candidate_id, 0.0)
        scored.append((score, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


async def get_related_questions(
    db: AsyncSession,
    question_id: int,
    limit: int = 5,
    exclude_statuses: list[str] | None = None,
    language: Language | str | ResponseLanguage = Language.JA,
) -> RelatedQuestions:
    """Related questions: embedding neighbours plus questions sharing concepts."""
    if exclude_statuses is None:
        exclude_statuses = ["REJECTED"]
    response = ResponseLanguage.of(language)
    lang = response.language

    question_similarity, questions_by_id = await _embedding_neighbours(
        db, question_id, lang, exclude_statuses
    )
    source_concept_ids, sharing = await _concept_neighbours(db, question_id)
    candidate_ids = set(question_similarity) | sharing
    await _load_missing(db, candidate_ids, questions_by_id, exclude_statuses)
    concept_similarity = await concept_repository.average_concept_similarity(
        db,
        source_concept_ids=source_concept_ids,
        candidate_question_ids=list(candidate_ids),
    )
    scored = _score(
        candidate_ids, questions_by_id, question_similarity, concept_similarity
    )

    # Filter before slicing, so a student still gets `limit` readable rows.
    ranked, missing = response.readable([candidate for _, candidate in scored])
    top_questions = ranked[:limit]
    needs = await prepare_for_response(db, top_questions, response)

    logger.info(
        "Related questions computed: question_id=%d candidates=%d returned=%d",
        question_id,
        len(candidate_ids),
        min(limit, len(scored)),
    )
    return RelatedQuestions(
        items=[QuestionResponse.model_validate(q) for q in top_questions],
        needs=TranslationNeeds(question_ids=missing).merge(needs),
    )
