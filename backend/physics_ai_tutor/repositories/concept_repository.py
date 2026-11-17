from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from physics_ai_tutor.core.text import normalize_key
from physics_ai_tutor.models import Concept, ConceptTerm, QuestionConcept


def build(
    embedding: list[float],
    extraction_model: str,
    embedding_model: str,
    extraction_prompt_version: str,
    name_ja: str | None = None,
    name_en: str | None = None,
) -> Concept:
    """A new, unsaved sense; given names become its preferred terms ([55])."""
    concept = Concept(
        name_ja=name_ja,
        name_en=name_en,
        embedding=embedding,
        extraction_model=extraction_model,
        embedding_model=embedding_model,
        extraction_prompt_version=extraction_prompt_version,
    )
    for language, word in (("ja", name_ja), ("en", name_en)):
        if word:
            concept.terms.append(
                ConceptTerm(
                    language=language,
                    term=word,
                    normalized=normalize_key(word),
                    is_preferred=True,
                    source="EXTRACTED",
                )
            )
    return concept


async def average_concept_similarity(
    db: AsyncSession,
    source_concept_ids: list[int],
    candidate_question_ids: list[int],
) -> dict[int, float]:
    """Average cosine similarity between each candidate question's concepts
    and the source question's concepts, grouped by candidate question id.

    Candidates with no linked concepts are simply absent from the result
    (callers should treat a missing entry as similarity 0).
    """
    if not source_concept_ids or not candidate_question_ids:
        return {}

    candidate_concept = aliased(Concept)
    source_concept = aliased(Concept)

    similarity = 1 - candidate_concept.embedding.cosine_distance(
        source_concept.embedding
    )

    query = (
        select(
            QuestionConcept.question_id,
            func.avg(similarity).label("avg_similarity"),
        )
        .join(candidate_concept, candidate_concept.id == QuestionConcept.concept_id)
        .join(source_concept, source_concept.id.in_(source_concept_ids))
        .where(QuestionConcept.question_id.in_(candidate_question_ids))
        .group_by(QuestionConcept.question_id)
    )
    rows = (await db.execute(query)).all()

    return {question_id: float(avg_similarity) for question_id, avg_similarity in rows}


async def ids_missing_name(
    db: AsyncSession, question_ids: list[int], language: str
) -> list[int]:
    """Concepts of these questions that have no name in `language`."""
    if not question_ids:
        return []
    column = Concept.name_ja if language == "ja" else Concept.name_en
    query = (
        select(Concept.id)
        .join(QuestionConcept, QuestionConcept.concept_id == Concept.id)
        .where(QuestionConcept.question_id.in_(question_ids), column.is_(None))
        .distinct()
    )
    return list((await db.scalars(query)).all())
