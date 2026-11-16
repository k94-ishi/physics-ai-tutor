from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.models import Concept, Question, QuestionConcept
from physics_ai_tutor.schemas.question import QuestionStatus


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


def _concepts_for_question_select(question_id: int):
    return (
        select(Concept)
        .join(QuestionConcept, QuestionConcept.concept_id == Concept.id)
        .where(QuestionConcept.question_id == question_id)
    )


def get_concepts_for_question(db: Session, question_id: int) -> list[Concept]:
    return list(db.scalars(_concepts_for_question_select(question_id)).all())


async def async_get_concepts_for_question(
    db: AsyncSession, question_id: int
) -> list[Concept]:
    """As `get_concepts_for_question` ([83])."""
    return list((await db.scalars(_concepts_for_question_select(question_id))).all())


async def async_get_concepts_for_questions(
    db: AsyncSession,
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
    """The strict-vs-fallback naming rule ([53])."""
    result: dict[int, list[str]] = {question_id: [] for question_id in question_ids}
    for question_id, concept in rows:
        name = concept.name_in(language) if strict else concept.display_name(language)
        if name is not None:
            result[question_id].append(name)

    return result


def _concept_ids_select(question_id: int):
    return select(QuestionConcept.concept_id).where(
        QuestionConcept.question_id == question_id
    )


def get_concept_ids_for_question(db: Session, question_id: int) -> list[int]:
    return list(db.scalars(_concept_ids_select(question_id)).all())


async def async_get_concept_ids_for_question(
    db: AsyncSession, question_id: int
) -> list[int]:
    """As `get_concept_ids_for_question` ([83])."""
    return list((await db.scalars(_concept_ids_select(question_id))).all())


async def get_questions_sharing_concepts(
    db: AsyncSession,
    question_id: int,
    exclude_ids: list[int],
    limit: int,
) -> list[int]:
    query = (
        select(QuestionConcept.question_id)
        .where(QuestionConcept.concept_id.in_(_concept_ids_select(question_id)))
        .where(QuestionConcept.question_id != question_id)
        .distinct()
    )

    if exclude_ids:
        query = query.where(QuestionConcept.question_id.notin_(exclude_ids))

    return list((await db.scalars(query.limit(limit))).all())


async def approved_links_sharing_concepts(
    db: AsyncSession, question_id: int
) -> list[tuple[Concept, Question]]:
    """Every APPROVED QA sharing a concept with this one, per shared concept ([38])."""
    query = (
        select(Concept, Question)
        .join(QuestionConcept, QuestionConcept.concept_id == Concept.id)
        .join(Question, Question.id == QuestionConcept.question_id)
        .where(
            Concept.id.in_(_concept_ids_select(question_id)),
            Question.id != question_id,
            Question.status == QuestionStatus.APPROVED,
        )
    )
    rows = (await db.execute(query)).all()

    return [(concept, question) for concept, question in rows]


async def async_delete_by_question_id(db: AsyncSession, question_id: int) -> None:
    """As `delete_by_question_id` ([91])."""
    await db.execute(
        sql_delete(QuestionConcept).where(QuestionConcept.question_id == question_id)
    )
    await db.flush()


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


async def async_context_question(
    db: AsyncSession, concept_id: int, language: str
) -> str | None:
    """A question text in `language` that uses the concept, for translation."""
    return (await db.scalars(_context_question_select(concept_id, language))).first()


async def async_link_many(
    db: AsyncSession, question_id: int, concept_ids: list[int]
) -> None:
    """Link a question to several concepts with one existence check."""
    existing = set(await async_get_concept_ids_for_question(db, question_id))
    new = [cid for cid in dict.fromkeys(concept_ids) if cid not in existing]
    db.add_all(QuestionConcept(question_id=question_id, concept_id=cid) for cid in new)
    await db.flush()
