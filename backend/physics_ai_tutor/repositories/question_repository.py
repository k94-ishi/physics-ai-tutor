from sqlalchemy import func, nullslast, or_
from sqlalchemy.orm import Query, Session

from physics_ai_tutor.models import AiReview, Question, QuestionAsk
from physics_ai_tutor.schemas.language import Language, TextProvenance
from physics_ai_tutor.schemas.question import QuestionCreate, QuestionUpdate


def _filter_by_keyword(
    query: Query,
    keyword: str | None,
    search_question: bool = True,
    search_answer: bool = True,
) -> Query:
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
            query = query.filter(or_(*conditions))

    return query


def _filter_by_status(
    query: Query,
    status: str | None,
    exclude_statuses: list[str] | None,
) -> Query:
    if status is not None:
        query = query.filter(Question.status == status)

    if exclude_statuses:
        query = query.filter(Question.status.notin_(exclude_statuses))

    return query


def _filter_by_language(query: Query, language: Language | str | None) -> Query:
    if language is None:
        return query

    return query.filter(getattr(Question, f"question_{Language(language)}").isnot(None))


def _with_latest_ai_review(db: Session, query):
    """Outer-join each question's newest ai_reviews row (one per question)."""
    latest = (
        db.query(AiReview.question_id, func.max(AiReview.id).label("latest_id"))
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
        return query.filter(AiReview.id.is_(None))

    return query.filter(AiReview.verdict == ai_verdict)


def _apply_sort(db: Session, query, sort: str | None):
    if sort == "oldest":
        return query.order_by(Question.created_at.asc(), Question.id.asc())

    if sort == "ai_confidence":
        return query.order_by(nullslast(AiReview.confidence.desc()), Question.id.asc())

    if sort == "asked_count":
        asks = (
            db.query(
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


def _list_query(
    db: Session,
    keyword: str | None,
    status: str | None,
    exclude_statuses: list[str] | None,
    search_question: bool,
    search_answer: bool,
    language: Language | str | None,
    ai_verdict: str | None,
    join_ai_review: bool,
):
    query = db.query(Question)

    if join_ai_review or ai_verdict is not None:
        query = _with_latest_ai_review(db, query)

    query = _filter_by_keyword(query, keyword, search_question, search_answer)
    query = _filter_by_status(query, status, exclude_statuses)
    query = _filter_by_language(query, language)

    return _filter_by_ai_verdict(query, ai_verdict)


def get_questions(
    db: Session,
    offset: int,
    limit: int,
    keyword: str | None = None,
    status: str | None = None,
    exclude_statuses: list[str] | None = None,
    search_question: bool = True,
    search_answer: bool = True,
    language: Language | str | None = None,
    sort: str | None = None,
    ai_verdict: str | None = None,
) -> list[Question]:
    query = _list_query(
        db,
        keyword,
        status,
        exclude_statuses,
        search_question,
        search_answer,
        language,
        ai_verdict,
        join_ai_review=sort == "ai_confidence",
    )

    return _apply_sort(db, query, sort).offset(offset).limit(limit).all()


def count_questions(
    db: Session,
    keyword: str | None = None,
    status: str | None = None,
    exclude_statuses: list[str] | None = None,
    search_question: bool = True,
    search_answer: bool = True,
    language: Language | str | None = None,
    ai_verdict: str | None = None,
) -> int:
    query = _list_query(
        db,
        keyword,
        status,
        exclude_statuses,
        search_question,
        search_answer,
        language,
        ai_verdict,
        join_ai_review=False,
    )

    return query.count()


def get_question(
    db: Session,
    question_id: int,
    exclude_statuses: list[str] | None = None,
) -> Question | None:
    query = db.query(Question).filter(Question.id == question_id)
    query = _filter_by_status(query, None, exclude_statuses)

    return query.first()


def get_questions_by_ids(db: Session, ids: list[int]) -> list[Question]:
    if not ids:
        return []

    return db.query(Question).filter(Question.id.in_(ids)).all()


def get_by_exact_text(
    db: Session,
    question_text: str,
    language: Language | str = Language.JA,
    exclude_statuses: list[str] | None = None,
) -> Question | None:
    column = getattr(Question, f"question_{Language(language)}")
    query = db.query(Question).filter(column == question_text)
    query = _filter_by_status(query, None, exclude_statuses)

    return query.first()


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
