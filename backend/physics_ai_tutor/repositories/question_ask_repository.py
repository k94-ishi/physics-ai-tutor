from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.models import Question, QuestionAsk


def _new_ask(
    question_id: int, user_id: int, language: str, cache_hit: bool
) -> QuestionAsk:
    return QuestionAsk(
        question_id=question_id,
        user_id=user_id,
        language=language,
        cache_hit=cache_hit,
    )


def create(
    db: Session,
    question_id: int,
    user_id: int,
    language: str,
    cache_hit: bool,
) -> QuestionAsk:
    ask = _new_ask(question_id, user_id, language, cache_hit)

    db.add(ask)
    db.flush()

    return ask


async def async_create(
    db: AsyncSession,
    question_id: int,
    user_id: int,
    language: str,
    cache_hit: bool,
) -> QuestionAsk:
    ask = _new_ask(question_id, user_id, language, cache_hit)

    db.add(ask)
    await db.flush()

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
