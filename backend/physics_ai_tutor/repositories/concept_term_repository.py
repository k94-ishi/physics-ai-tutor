from sqlalchemy import func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.models import Concept, ConceptTerm, Question, QuestionConcept


def senses_with_any_term(db: Session, normalized: str) -> list[Concept]:
    """Senses having this word in either language."""
    return (
        db.query(Concept)
        .join(ConceptTerm, ConceptTerm.concept_id == Concept.id)
        .filter(ConceptTerm.normalized == normalized)
        .distinct()
        .all()
    )


async def search_terms(db: AsyncSession, needle: str, limit: int) -> list[ConceptTerm]:
    """Terms containing the normalised needle, either language."""
    query = (
        select(ConceptTerm)
        .where(ConceptTerm.normalized.contains(needle, autoescape=True))
        .limit(limit)
    )
    return list((await db.scalars(query)).all())


def _question_counts_select(concept_ids: list[int], statuses: list[str] | None):
    query = select(QuestionConcept.concept_id, func.count()).where(
        QuestionConcept.concept_id.in_(concept_ids)
    )
    if statuses is not None:
        query = query.join(Question, Question.id == QuestionConcept.question_id).where(
            Question.status.in_(statuses)
        )
    return query.group_by(QuestionConcept.concept_id)


async def question_counts(
    db: AsyncSession, concept_ids: list[int], statuses: list[str] | None
) -> dict[int, int]:
    """Linked questions per sense, optionally limited to some statuses."""
    if not concept_ids:
        return {}
    rows = (await db.execute(_question_counts_select(concept_ids, statuses))).all()
    return {concept_id: count for concept_id, count in rows}


async def get_term(db: AsyncSession, term_id: int) -> ConceptTerm | None:
    return await db.get(ConceptTerm, term_id)


async def linked_question_ids(db: AsyncSession, concept_id: int) -> list[int]:
    query = select(QuestionConcept.question_id).where(
        QuestionConcept.concept_id == concept_id
    )
    return list((await db.scalars(query)).all())


async def links_of(db: AsyncSession, concept_id: int) -> list[QuestionConcept]:
    query = select(QuestionConcept).where(QuestionConcept.concept_id == concept_id)
    return list((await db.scalars(query)).all())


async def move_links(
    db: AsyncSession, from_id: int, to_id: int, question_ids: list[int]
) -> None:
    """Point these questions' links at another sense ([55] split)."""
    await db.execute(
        update(QuestionConcept)
        .where(
            QuestionConcept.concept_id == from_id,
            QuestionConcept.question_id.in_(question_ids),
        )
        .values(concept_id=to_id)
        .execution_options(synchronize_session=False)
    )


def get_many(db: Session, concept_ids: list[int]) -> list[Concept]:
    if not concept_ids:
        return []
    return list(db.scalars(select(Concept).where(Concept.id.in_(concept_ids))).all())


async def async_get_many(db: AsyncSession, concept_ids: list[int]) -> list[Concept]:
    """As `get_many` ([84]); `Concept.terms` loads eagerly (selectin)."""
    if not concept_ids:
        return []
    query = select(Concept).where(Concept.id.in_(concept_ids))
    return list((await db.scalars(query)).all())


async def most_linked(
    db: AsyncSession, statuses: list[str] | None, limit: int
) -> list[int]:
    """Senses with the most linked questions."""
    query = select(QuestionConcept.concept_id, func.count().label("n"))
    if statuses is not None:
        query = query.join(Question, Question.id == QuestionConcept.question_id).where(
            Question.status.in_(statuses)
        )
    query = (
        query.group_by(QuestionConcept.concept_id)
        .order_by(func.count().desc(), QuestionConcept.concept_id)
        .limit(limit)
    )
    return [concept_id for concept_id, _ in (await db.execute(query)).all()]


def _shared_words_subquery():
    # (language, normalized) pairs used by more than one sense.
    return (
        select(ConceptTerm.language, ConceptTerm.normalized)
        .group_by(ConceptTerm.language, ConceptTerm.normalized)
        .having(func.count(func.distinct(ConceptTerm.concept_id)) > 1)
        .subquery()
    )


async def admin_concept_ids(
    db: AsyncSession, needle: str, review_filter: str
) -> list[int]:
    """Sense ids for the admin editor, newest first.

    review_filter: "all", "review" (machine words or a language without a
    word), or "shared" (a word also used by another sense).
    """
    query = select(Concept.id)
    if needle:
        query = query.where(
            Concept.id.in_(
                select(ConceptTerm.concept_id).where(
                    ConceptTerm.normalized.contains(needle, autoescape=True)
                )
            )
        )
    if review_filter == "review":
        machine = select(ConceptTerm.concept_id).where(ConceptTerm.source == "MACHINE")
        query = query.where(
            Concept.id.in_(machine)
            | Concept.name_ja.is_(None)
            | Concept.name_en.is_(None)
        )
    elif review_filter == "shared":
        shared = _shared_words_subquery()
        query = query.where(
            Concept.id.in_(
                select(ConceptTerm.concept_id).join(
                    shared,
                    (shared.c.language == ConceptTerm.language)
                    & (shared.c.normalized == ConceptTerm.normalized),
                )
            )
        )
    return list((await db.scalars(query.order_by(Concept.id.desc()))).all())


def _partners_select(concept_ids: list[int]):
    mine = (
        select(ConceptTerm.language, ConceptTerm.normalized, ConceptTerm.concept_id)
        .where(ConceptTerm.concept_id.in_(concept_ids))
        .subquery()
    )
    return (
        select(mine.c.concept_id, ConceptTerm.concept_id)
        .join(
            ConceptTerm,
            (ConceptTerm.language == mine.c.language)
            & (ConceptTerm.normalized == mine.c.normalized)
            & (ConceptTerm.concept_id != mine.c.concept_id),
        )
        .distinct()
    )


def _partners_by_sense(rows) -> dict[int, list[int]]:
    result: dict[int, list[int]] = {}
    for own, other in rows:
        result.setdefault(own, []).append(other)
    return {key: sorted(value) for key, value in result.items()}


async def shared_word_partners(
    db: AsyncSession, concept_ids: list[int]
) -> dict[int, list[int]]:
    """For each sense, the other senses that share one of its words."""
    if not concept_ids:
        return {}
    rows = (await db.execute(_partners_select(concept_ids))).all()
    return _partners_by_sense(rows)


def _linked_questions_select(concept_id: int):
    return (
        select(Question)
        .join(QuestionConcept, QuestionConcept.question_id == Question.id)
        .where(QuestionConcept.concept_id == concept_id)
        .order_by(Question.id)
    )


def _resolved(questions: list[Question], language: str) -> list[Question]:
    for question in questions:
        question.resolve(language)
    return questions


async def linked_questions(
    db: AsyncSession, concept_id: int, language: str
) -> list[Question]:
    rows = await db.scalars(_linked_questions_select(concept_id))
    return _resolved(list(rows.all()), language)


WordKey = tuple[str, str]


def senses_by_words(db: Session, keys: set[WordKey]) -> dict[WordKey, list[Concept]]:
    """For each (language, normalized) word, the senses that have it.

    Two queries for any number of words, instead of one lookup per word.
    """
    if not keys:
        return {}
    rows = (
        db.query(ConceptTerm.language, ConceptTerm.normalized, ConceptTerm.concept_id)
        .filter(tuple_(ConceptTerm.language, ConceptTerm.normalized).in_(list(keys)))
        .all()
    )
    concepts = {c.id: c for c in get_many(db, list({cid for _, _, cid in rows}))}
    index: dict[WordKey, list[Concept]] = {}
    for language, normalized, concept_id in rows:
        index.setdefault((language, normalized), []).append(concepts[concept_id])
    return index
