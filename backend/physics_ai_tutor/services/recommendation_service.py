import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.repositories import (
    concept_repository,
    embedding_repository,
    question_concept_repository,
    question_repository,
)
from physics_ai_tutor.schemas.question import QuestionResponse
from physics_ai_tutor.services.question_service import (
    attach_concept_names,
    attach_retrieved_questions,
)

logger = logging.getLogger(__name__)

# Kept as simple, named constants so the relative weighting of question vs.
# concept similarity can be tuned later without touching the algorithm.
QUESTION_SIMILARITY_WEIGHT = 0.7
CONCEPT_SIMILARITY_WEIGHT = 0.3

CANDIDATE_POOL_SIZE = 50


def get_related_questions(
    db: Session,
    question_id: int,
    limit: int = 5,
    exclude_statuses: list[str] | None = None,
) -> list[QuestionResponse]:
    if exclude_statuses is None:
        exclude_statuses = ["REJECTED"]

    question_similarity: dict[int, float] = {}
    questions_by_id = {}

    source_embedding = embedding_repository.get_embedding(db, question_id, "question")

    if source_embedding is not None:
        embedding_rows = embedding_repository.search_similar_embeddings(
            db,
            embedding=source_embedding,
            embedding_type="question",
            limit=CANDIDATE_POOL_SIZE,
            exclude_question_ids=[question_id],
            exclude_statuses=exclude_statuses,
        )

        for _, question, distance in embedding_rows:
            question_similarity[question.id] = 1 - distance
            questions_by_id[question.id] = question

    # RAG生成結果の場合、回答生成時に参考にした既存QA(retrieved_question_ids)の
    # Conceptも関連質問探索の手がかりに加える(新しい検索・LLM呼び出しは追加せず、
    # 既存のConcept検索関数をRAG参考QAに対しても呼ぶだけ)。
    source_question = question_repository.get_question(db, question_id)
    reference_ids = source_question.retrieved_question_ids if source_question else []

    source_concepts = question_concept_repository.get_concepts_for_question(
        db, question_id
    )
    source_concept_id_set = {concept.id for concept in source_concepts}
    for reference_id in reference_ids:
        source_concept_id_set.update(
            question_concept_repository.get_concept_ids_for_question(db, reference_id)
        )
    source_concept_ids = list(source_concept_id_set)

    shared_concept_question_ids = set(
        question_concept_repository.get_questions_sharing_concepts(
            db,
            question_id=question_id,
            exclude_ids=[question_id],
            limit=CANDIDATE_POOL_SIZE,
        )
    )
    for reference_id in reference_ids:
        shared_concept_question_ids.update(
            question_concept_repository.get_questions_sharing_concepts(
                db,
                question_id=reference_id,
                exclude_ids=[question_id, *reference_ids],
                limit=CANDIDATE_POOL_SIZE,
            )
        )

    candidate_ids = set(question_similarity) | shared_concept_question_ids

    for candidate_id in candidate_ids:
        if candidate_id not in questions_by_id:
            question = question_repository.get_question(db, candidate_id)
            if question is not None and question.status not in exclude_statuses:
                questions_by_id[candidate_id] = question

    concept_similarity = concept_repository.average_concept_similarity(
        db,
        source_concept_ids=source_concept_ids,
        candidate_question_ids=list(candidate_ids),
    )

    scored = []
    for candidate_id in candidate_ids:
        question = questions_by_id.get(candidate_id)
        if question is None:
            continue

        score = QUESTION_SIMILARITY_WEIGHT * question_similarity.get(
            candidate_id, 0.0
        ) + CONCEPT_SIMILARITY_WEIGHT * concept_similarity.get(candidate_id, 0.0)
        scored.append((score, question))

    scored.sort(key=lambda item: item[0], reverse=True)

    top_questions = [question for _, question in scored[:limit]]
    attach_concept_names(db, top_questions)
    attach_retrieved_questions(db, top_questions)

    logger.info(
        "Related questions computed: question_id=%d candidates=%d returned=%d",
        question_id,
        len(candidate_ids),
        min(limit, len(scored)),
    )

    return [QuestionResponse.model_validate(question) for question in top_questions]
