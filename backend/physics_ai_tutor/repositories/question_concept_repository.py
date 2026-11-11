from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.models import Concept, Question, QuestionConcept


def link(db: Session, question_id: int, concept_id: int) -> None:
    exists = (
        db.query(QuestionConcept)
        .filter(
            QuestionConcept.question_id == question_id,
            QuestionConcept.concept_id == concept_id,
        )
        .first()
    )

    if exists is not None:
        return

    db.add(QuestionConcept(question_id=question_id, concept_id=concept_id))
    db.flush()


def get_concepts_for_question(db: Session, question_id: int) -> list[Concept]:
    return (
        db.query(Concept)
        .join(QuestionConcept, QuestionConcept.concept_id == Concept.id)
        .filter(QuestionConcept.question_id == question_id)
        .all()
    )


def get_concepts_for_questions(
    db: Session,
    question_ids: list[int],
    language: str = "ja",
    strict: bool = False,
) -> dict[int, list[str]]:
    """Concept names per question in `language`.

    Falls back to the other language unless `strict` is set, in
    which case concepts without a name in `language` are skipped.
    """
    if not question_ids:
        return {}

    rows = db.execute(_concepts_for_questions_select(question_ids)).all()

    return _names_by_question(rows, question_ids, language, strict)


async def async_get_concepts_for_questions(
    db: AsyncSession,
    question_ids: list[int],
    language: str = "ja",
    strict: bool = False,
) -> dict[int, list[str]]:
    """As `get_concepts_for_questions` ([70])."""
    if not question_ids:
        return {}

    rows = (await db.execute(_concepts_for_questions_select(question_ids))).all()

    return _names_by_question(rows, question_ids, language, strict)


def _concepts_for_questions_select(question_ids: list[int]):
    return (
        select(QuestionConcept.question_id, Concept)
        .join(Concept, Concept.id == QuestionConcept.concept_id)
        .where(QuestionConcept.question_id.in_(question_ids))
    )


def _names_by_question(
    rows, question_ids: list[int], language: str, strict: bool
) -> dict[int, list[str]]:
    """The strict-vs-fallback naming rule, shared by both variants ([53])."""
    result: dict[int, list[str]] = {question_id: [] for question_id in question_ids}
    for question_id, concept in rows:
        name = concept.name_in(language) if strict else concept.display_name(language)
        if name is not None:
            result[question_id].append(name)

    return result


def get_concept_ids_for_question(db: Session, question_id: int) -> list[int]:
    rows = (
        db.query(QuestionConcept.concept_id)
        .filter(QuestionConcept.question_id == question_id)
        .all()
    )

    return [concept_id for (concept_id,) in rows]


def get_questions_sharing_concepts(
    db: Session,
    question_id: int,
    exclude_ids: list[int],
    limit: int,
) -> list[int]:
    concept_ids_subquery = (
        db.query(QuestionConcept.concept_id)
        .filter(QuestionConcept.question_id == question_id)
        .scalar_subquery()
    )

    query = (
        db.query(QuestionConcept.question_id)
        .filter(QuestionConcept.concept_id.in_(concept_ids_subquery))
        .filter(QuestionConcept.question_id != question_id)
        .distinct()
    )

    if exclude_ids:
        query = query.filter(QuestionConcept.question_id.notin_(exclude_ids))

    rows = query.limit(limit).all()

    return [related_id for (related_id,) in rows]


def delete_by_question_id(db: Session, question_id: int) -> None:
    (
        db.query(QuestionConcept)
        .filter(QuestionConcept.question_id == question_id)
        .delete()
    )
    db.flush()


def _context_question_select(concept_id: int, language: str):
    column = Question.question_ja if language == "ja" else Question.question_en
    return (
        select(column)
        .join(QuestionConcept, QuestionConcept.question_id == Question.id)
        .where(QuestionConcept.concept_id == concept_id, column.is_not(None))
        .order_by(Question.status != "APPROVED", Question.id)
        .limit(1)
    )


def context_question(db: Session, concept_id: int, language: str) -> str | None:
    """A question text in `language` that uses the concept, for translation."""
    return db.scalars(_context_question_select(concept_id, language)).first()


async def async_context_question(
    db: AsyncSession, concept_id: int, language: str
) -> str | None:
    """A question text in `language` that uses the concept, for translation."""
    return (await db.scalars(_context_question_select(concept_id, language))).first()


def link_many(db: Session, question_id: int, concept_ids: list[int]) -> None:
    """Link a question to several concepts with one existence check."""
    existing = set(get_concept_ids_for_question(db, question_id))
    new = [cid for cid in dict.fromkeys(concept_ids) if cid not in existing]
    db.add_all(QuestionConcept(question_id=question_id, concept_id=cid) for cid in new)
    db.flush()
