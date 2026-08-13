from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from physics_ai_tutor.models.question import Question
from physics_ai_tutor.schemas.question import QuestionCreate, QuestionUpdate


def _filter_by_keyword(query: Query, keyword: str | None) -> Query:
    if not keyword:
        return query

    pattern = f"%{keyword}%"

    return query.filter(
        or_(
            Question.question.ilike(pattern),
            Question.answer.ilike(pattern),
        )
    )


def _filter_by_status(
    query: Query,
    status: str | None,
    exclude_status: str | None,
) -> Query:
    if status is not None:
        query = query.filter(Question.status == status)

    if exclude_status is not None:
        query = query.filter(Question.status != exclude_status)

    return query


def get_questions(
    db: Session,
    offset: int,
    limit: int,
    keyword: str | None = None,
    status: str | None = None,
    exclude_status: str | None = None,
) -> list[Question]:
    query = _filter_by_keyword(db.query(Question), keyword)
    query = _filter_by_status(query, status, exclude_status)

    return (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_questions(
    db: Session,
    keyword: str | None = None,
    status: str | None = None,
    exclude_status: str | None = None,
) -> int:
    query = _filter_by_keyword(db.query(Question), keyword)
    query = _filter_by_status(query, status, exclude_status)

    return query.count()


def get_question(
    db: Session,
    question_id: int,
    exclude_status: str | None = None,
) -> Question:
    query = db.query(Question).filter(Question.id == question_id)
    query = _filter_by_status(query, None, exclude_status)

    return query.first()


def get_by_exact_text(db: Session, question_text: str) -> Question | None:
    return (
        db.query(Question)
        .filter(Question.question == question_text)
        .first()
    )


def create_question(
    db: Session,
    question: str,
    answer: str,
    status: str = "APPROVED",
    source: str = "MANUAL",
):
    db_question = Question(
        question=question,
        answer=answer,
        status=status,
        source=source,
    )

    db.add(db_question)
    db.flush()

    return db_question


def create_questions(
    db: Session,
    questions: list[QuestionCreate],
    status: str = "APPROVED",
    source: str = "MANUAL",
):
    db_questions = [
        Question(
            question=q.question,
            answer=q.answer,
            status=status,
            source=source,
        )
        for q in questions
    ]

    db.add_all(db_questions)
    db.flush()

    return db_questions


def delete(db: Session, question_id: int) -> bool:
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if not question:
        return False

    db.delete(question)
    db.flush()

    return True


def update(
    db: Session,
    question_id: int,
    question_data: QuestionUpdate,
) -> Question | None:
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if not question:
        return None

    question.question = question_data.question
    question.answer = question_data.answer

    db.flush()

    return question


def update_content_and_status(
    db: Session,
    question_id: int,
    status: str,
    question: str | None = None,
    answer: str | None = None,
) -> Question | None:
    db_question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if not db_question:
        return None

    if question is not None:
        db_question.question = question
    if answer is not None:
        db_question.answer = answer
    db_question.status = status

    db.flush()

    return db_question
