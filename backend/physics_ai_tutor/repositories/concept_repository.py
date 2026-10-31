from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from physics_ai_tutor.models import Concept, QuestionConcept


def get_by_name(db: Session, name: str, language: str = "ja") -> Concept | None:
    column = Concept.name_ja if language == "ja" else Concept.name_en
    return db.query(Concept).filter(column == name).first()


def create(
    db: Session,
    embedding: list[float],
    extraction_model: str,
    embedding_model: str,
    extraction_prompt_version: str,
    name_ja: str | None = None,
    name_en: str | None = None,
    name: str | None = None,
) -> Concept:
    # Legacy single-name form means Japanese.
    if name is not None:
        name_ja = name

    if name_ja is None and name_en is None:
        raise ValueError("A concept needs a name in at least one language")

    concept = Concept(
        name_ja=name_ja,
        name_en=name_en,
        embedding=embedding,
        extraction_model=extraction_model,
        embedding_model=embedding_model,
        extraction_prompt_version=extraction_prompt_version,
    )

    db.add(concept)
    db.flush()

    return concept


def list_all(db: Session) -> list[Concept]:
    return db.query(Concept).all()


def average_concept_similarity(
    db: Session,
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

    rows = (
        db.query(
            QuestionConcept.question_id,
            func.avg(similarity).label("avg_similarity"),
        )
        .join(candidate_concept, candidate_concept.id == QuestionConcept.concept_id)
        .join(source_concept, source_concept.id.in_(source_concept_ids))
        .filter(QuestionConcept.question_id.in_(candidate_question_ids))
        .group_by(QuestionConcept.question_id)
        .all()
    )

    return {question_id: float(avg_similarity) for question_id, avg_similarity in rows}
