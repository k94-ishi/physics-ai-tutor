from sqlalchemy import func, nullslast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.core.text import normalize_key
from physics_ai_tutor.models import (
    AiReview,
    Concept,
    ConceptTerm,
    Question,
    QuestionAsk,
    QuestionConcept,
)
from physics_ai_tutor.schemas.language import Language, TextProvenance
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionFilters,
    QuestionUpdate,
)


def _filter_by_concept(query, concept: str | None, concept_id: int | None = None):
    """Keep questions linked to a concept sense ([55]).

    `concept_id` names one sense exactly. A `concept` word matches every
    sense having that word in either language, so a chip or a typed word
    finds QAs whatever language their concept was first named in.
    """
    if concept_id is not None:
        senses = select(Concept.id).where(Concept.id == concept_id)
    elif concept:
        senses = select(ConceptTerm.concept_id).where(
            ConceptTerm.normalized == normalize_key(concept)
        )
    else:
        return query

    linked = (
        select(QuestionConcept.question_id)
        .where(QuestionConcept.concept_id.in_(senses.scalar_subquery()))
        .scalar_subquery()
    )

    return query.where(Question.id.in_(linked))


def _filter_by_keyword(
    query,
    keyword: str | None,
    search_question: bool = True,
    search_answer: bool = True,
):
    if not keyword:
        return query

    # Space-separated AND search; each term may match any language column.
    for term in keyword.split():
        pattern = f"%{term}%"
        conditions = []

        if search_question:
            conditions.append(Question.question_ja.ilike(pattern))
            conditions.append(Question.question_en.ilike(pattern))
        if search_answer:
            conditions.append(Question.answer_ja.ilike(pattern))
            conditions.append(Question.answer_en.ilike(pattern))

        if conditions:
            query = query.where(or_(*conditions))

    return query


def _status_conditions(status: str | None, exclude_statuses: list[str] | None) -> list:
    """The status predicate, shared by every reader.

    Security-relevant: `exclude_statuses` is what keeps unapproved rows
    away from students and REJECTED answers out of the ask cache, so every
    statement must build it from here rather than spelling it out.
    """
    conditions = []

    if status is not None:
        conditions.append(Question.status == status)

    if exclude_statuses:
        conditions.append(Question.status.notin_(exclude_statuses))

    return conditions


def _filter_by_status(
    query,
    status: str | None,
    exclude_statuses: list[str] | None,
):
    for condition in _status_conditions(status, exclude_statuses):
        query = query.where(condition)

    return query


def _filter_by_language(query, language: Language | str | None):
    if language is None:
        return query

    return query.where(getattr(Question, f"question_{Language(language)}").isnot(None))


def _with_latest_ai_review(query):
    """Outer-join each question's newest ai_reviews row (one per question)."""
    latest = (
        select(AiReview.question_id, func.max(AiReview.id).label("latest_id"))
        .group_by(AiReview.question_id)
        .subquery()
    )

    return query.outerjoin(latest, latest.c.question_id == Question.id).outerjoin(
        AiReview, AiReview.id == latest.c.latest_id
    )


def _filter_by_ai_verdict(query, ai_verdict: str | None):
    if ai_verdict is None:
        return query
    if ai_verdict == "NONE":
        return query.where(AiReview.id.is_(None))

    return query.where(AiReview.verdict == ai_verdict)


def _apply_sort(query, sort: str | None):
    if sort == "oldest":
        return query.order_by(Question.created_at.asc(), Question.id.asc())

    if sort == "ai_confidence":
        return query.order_by(nullslast(AiReview.confidence.desc()), Question.id.asc())

    if sort == "asked_count":
        asks = (
            select(
                QuestionAsk.question_id,
                func.count(QuestionAsk.id).label("asked"),
            )
            .group_by(QuestionAsk.question_id)
            .subquery()
        )
        return query.outerjoin(asks, asks.c.question_id == Question.id).order_by(
            func.coalesce(asks.c.asked, 0).desc(), Question.id.asc()
        )

    return query.order_by(Question.id)


def _list_select(filters: QuestionFilters, join_ai_review: bool):
    """The list statement; one builder so no filter can differ by caller."""
    query = select(Question)

    if join_ai_review or filters.ai_verdict is not None:
        query = _with_latest_ai_review(query)

    if filters.ids is not None:
        query = query.where(Question.id.in_(filters.ids))

    query = _filter_by_concept(query, filters.concept, filters.concept_id)
    query = _filter_by_keyword(
        query, filters.keyword, filters.search_question, filters.search_answer
    )
    query = _filter_by_status(query, filters.status, filters.exclude_statuses)
    query = _filter_by_language(query, filters.language)

    return _filter_by_ai_verdict(query, filters.ai_verdict)


async def get_questions(
    db: AsyncSession,
    offset: int,
    limit: int,
    filters: QuestionFilters | None = None,
    sort: str | None = None,
) -> list[Question]:
    query = _list_select(
        filters or QuestionFilters(), join_ai_review=sort == "ai_confidence"
    )
    page = _apply_sort(query, sort).offset(offset).limit(limit)

    return list((await db.scalars(page)).all())


async def count_questions(
    db: AsyncSession, filters: QuestionFilters | None = None
) -> int:
    query = _list_select(filters or QuestionFilters(), join_ai_review=False)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))

    return total or 0


def _question_select(question_id: int, exclude_statuses: list[str] | None):
    query = select(Question).where(Question.id == question_id)

    return _filter_by_status(query, None, exclude_statuses)


def get_question(
    db: Session,
    question_id: int,
    exclude_statuses: list[str] | None = None,
) -> Question | None:
    return db.scalars(_question_select(question_id, exclude_statuses)).first()


async def async_get_question(
    db: AsyncSession,
    question_id: int,
    exclude_statuses: list[str] | None = None,
) -> Question | None:
    """As `get_question` ([83]); the sync one serves the admin writers."""
    return (await db.scalars(_question_select(question_id, exclude_statuses))).first()


def get_questions_by_ids(db: Session, ids: list[int]) -> list[Question]:
    if not ids:
        return []

    return list(db.scalars(select(Question).where(Question.id.in_(ids))).all())


async def async_get_questions_by_ids(
    db: AsyncSession, ids: list[int]
) -> list[Question]:
    if not ids:
        return []

    return list((await db.scalars(select(Question).where(Question.id.in_(ids)))).all())


def _exact_text_select(
    question_text: str,
    language: Language | str,
    exclude_statuses: list[str] | None,
):
    column = getattr(Question, f"question_{Language(language)}")

    return select(Question).where(
        column == question_text, *_status_conditions(None, exclude_statuses)
    )


def get_by_exact_text(
    db: Session,
    question_text: str,
    language: Language | str = Language.JA,
    exclude_statuses: list[str] | None = None,
) -> Question | None:
    query = _exact_text_select(question_text, language, exclude_statuses)

    return db.scalars(query).first()


async def async_get_by_exact_text(
    db: AsyncSession,
    question_text: str,
    language: Language | str = Language.JA,
    exclude_statuses: list[str] | None = None,
) -> Question | None:
    query = _exact_text_select(question_text, language, exclude_statuses)

    return (await db.scalars(query)).first()


def get_missing_language(
    db: Session, language: Language | str, limit: int | None = None
) -> list[Question]:
    """Questions that have no text in `language` (candidates for translation)."""
    column = getattr(Question, f"question_{Language(language)}")
    query = db.query(Question).filter(column.is_(None)).order_by(Question.id)

    if limit is not None:
        query = query.limit(limit)

    return query.all()


def _new_question(
    texts: dict[Language, tuple[str, str]],
    original_language: Language | str,
    status: str,
    source: str,
    retrieved_question_ids: list[int] | None,
    provenances: dict[Language, str] | None,
) -> Question:
    original = Language(original_language)
    question = Question(
        original_language=original.value,
        status=status,
        source=source,
        retrieved_question_ids=retrieved_question_ids or [],
    )

    for lang, (q, a) in texts.items():
        if provenances and lang in provenances:
            provenance = provenances[lang]
        elif lang == original:
            provenance = TextProvenance.ORIGINAL
        else:
            provenance = TextProvenance.HUMAN
        question.set_text(lang, q, a, provenance)

    return question


def create_question(
    db: Session,
    texts: dict[Language, tuple[str, str]] | None = None,
    original_language: Language | str = Language.JA,
    status: str = "APPROVED",
    source: str = "MANUAL",
    retrieved_question_ids: list[int] | None = None,
    provenances: dict[Language, str] | None = None,
    question: str | None = None,
    answer: str | None = None,
    language: Language | str = Language.JA,
) -> Question:
    # Legacy single-language form: question=/answer=/language=.
    if texts is None:
        if question is None or answer is None:
            raise ValueError("Either texts or question and answer are required")
        texts = {Language(language): (question, answer)}
        original_language = language

    db_question = _new_question(
        texts, original_language, status, source, retrieved_question_ids, provenances
    )

    db.add(db_question)
    db.flush()

    return db_question


async def async_create_question(
    db: AsyncSession,
    texts: dict[Language, tuple[str, str]],
    original_language: Language | str = Language.JA,
    status: str = "APPROVED",
    source: str = "MANUAL",
    retrieved_question_ids: list[int] | None = None,
) -> Question:
    """As `create_question`, without the legacy single-language form ([70])."""
    db_question = _new_question(
        texts, original_language, status, source, retrieved_question_ids, None
    )

    db.add(db_question)
    await db.flush()

    return db_question


def create_questions(
    db: Session,
    rows: list[tuple[dict[Language, tuple[str, str]], Language] | QuestionCreate],
    status: str = "APPROVED",
    source: str = "MANUAL",
) -> list[Question]:
    normalised = [
        (row.texts(), row.original_language())
        if isinstance(row, QuestionCreate)
        else row
        for row in rows
    ]
    db_questions = [
        _new_question(texts, original, status, source, None, None)
        for texts, original in normalised
    ]

    db.add_all(db_questions)
    db.flush()

    return db_questions


def delete(db: Session, question_id: int) -> bool:
    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        return False

    db.delete(question)
    db.flush()

    return True


def set_text(
    db: Session,
    question_id: int,
    language: Language | str,
    question: str,
    answer: str,
    provenance: str,
) -> Question | None:
    db_question = db.query(Question).filter(Question.id == question_id).first()

    if not db_question:
        return None

    db_question.set_text(language, question, answer, provenance)
    db.flush()

    return db_question


async def async_update_status(
    db: AsyncSession, question_id: int, status: str
) -> Question | None:
    """As `update_status` ([85])."""
    db_question = await db.get(Question, question_id)

    if not db_question:
        return None

    db_question.status = status
    await db.flush()

    return db_question


def update_status(db: Session, question_id: int, status: str) -> Question | None:
    db_question = db.query(Question).filter(Question.id == question_id).first()

    if not db_question:
        return None

    db_question.status = status
    db.flush()

    return db_question


def update(
    db: Session,
    question_id: int,
    question_data: QuestionUpdate,
) -> Question | None:
    """Replace the given languages' text (human-provided)."""
    db_question = db.query(Question).filter(Question.id == question_id).first()

    if not db_question:
        return None

    for lang, (q, a) in question_data.texts().items():
        provenance = (
            TextProvenance.ORIGINAL
            if lang == db_question.original_language
            else TextProvenance.HUMAN
        )
        db_question.set_text(lang, q, a, provenance)

    db.flush()

    return db_question


def update_content_and_status(
    db: Session,
    question_id: int,
    status: str,
    question: str | None = None,
    answer: str | None = None,
    language: Language | str | None = None,
) -> Question | None:
    """Set status and optionally replace one language's text."""
    db_question = db.query(Question).filter(Question.id == question_id).first()

    if not db_question:
        return None

    if question is not None and answer is not None:
        lang = (
            Language(language) if language else Language(db_question.original_language)
        )
        provenance = (
            TextProvenance.ORIGINAL
            if lang == db_question.original_language
            else TextProvenance.HUMAN
        )
        db_question.set_text(lang, question, answer, provenance)

    db_question.status = status
    db.flush()

    return db_question
