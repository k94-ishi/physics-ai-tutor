from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from physics_ai_tutor.models.question import Question
from physics_ai_tutor.schemas.question import QuestionCreate, QuestionUpdate


def _filter_by_keyword(
    query: Query,
    keyword: str | None,
    search_question: bool = True,
    search_answer: bool = True,
) -> Query:
    if not keyword:
        return query

    # スペース区切りのAND検索。各語について、質問/回答のうち指定された列を
    # OR で検索する(シンプルな実装で十分なため、引用符やNOT等は非対応)。
    for term in keyword.split():
        pattern = f"%{term}%"
        conditions = []

        if search_question:
            conditions.append(Question.question.ilike(pattern))
        if search_answer:
            conditions.append(Question.answer.ilike(pattern))

        if conditions:
            query = query.filter(or_(*conditions))

    return query


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
    search_question: bool = True,
    search_answer: bool = True,
) -> list[Question]:
    query = _filter_by_keyword(
        db.query(Question), keyword, search_question, search_answer
    )
    query = _filter_by_status(query, status, exclude_status)

    return query.offset(offset).limit(limit).all()


def count_questions(
    db: Session,
    keyword: str | None = None,
    status: str | None = None,
    exclude_status: str | None = None,
    search_question: bool = True,
    search_answer: bool = True,
) -> int:
    query = _filter_by_keyword(
        db.query(Question), keyword, search_question, search_answer
    )
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


def get_questions_by_ids(db: Session, ids: list[int]) -> list[Question]:
    if not ids:
        return []

    return db.query(Question).filter(Question.id.in_(ids)).all()


def get_by_exact_text(
    db: Session,
    question_text: str,
    exclude_status: str | None = None,
) -> Question | None:
    query = db.query(Question).filter(Question.question == question_text)
    query = _filter_by_status(query, None, exclude_status)

    return query.first()


def create_question(
    db: Session,
    question: str,
    answer: str,
    status: str = "APPROVED",
    source: str = "MANUAL",
    retrieved_question_ids: list[int] | None = None,
):
    db_question = Question(
        question=question,
        answer=answer,
        status=status,
        source=source,
        retrieved_question_ids=retrieved_question_ids or [],
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
    question = db.query(Question).filter(Question.id == question_id).first()

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
    question = db.query(Question).filter(Question.id == question_id).first()

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
    db_question = db.query(Question).filter(Question.id == question_id).first()

    if not db_question:
        return None

    if question is not None:
        db_question.question = question
    if answer is not None:
        db_question.answer = answer
    db_question.status = status

    db.flush()

    return db_question
