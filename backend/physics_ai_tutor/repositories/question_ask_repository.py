from sqlalchemy import func
from sqlalchemy.orm import Session

from physics_ai_tutor.models import Question, QuestionAsk


def create(
    db: Session,
    question_id: int,
    user_id: int,
    language: str,
) -> QuestionAsk:
    ask = QuestionAsk(
        question_id=question_id,
        user_id=user_id,
        language=language,
    )

    db.add(ask)
    db.flush()

    return ask


def list_for_user(
    db: Session,
    user_id: int,
    offset: int,
    limit: int,
) -> list[tuple[QuestionAsk, Question]]:

    rows = (
        db.query(QuestionAsk, Question)
        .join(Question, QuestionAsk.question_id == Question.id)
        .filter(QuestionAsk.user_id == user_id)
        .order_by(QuestionAsk.created_at.desc(), QuestionAsk.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [(ask, question) for ask, question in rows]


def count_for_user(
    db: Session,
    user_id: int,
) -> int:

    return (
        db.query(func.count(QuestionAsk.id))
        .filter(QuestionAsk.user_id == user_id)
        .scalar()
    ) or 0
