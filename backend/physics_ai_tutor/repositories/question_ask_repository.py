from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def create(
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


async def list_for_user(
    db: AsyncSession,
    user_id: int,
    offset: int,
    limit: int,
) -> list[tuple[QuestionAsk, Question]]:
    rows = (
        await db.execute(
            select(QuestionAsk, Question)
            .join(Question, QuestionAsk.question_id == Question.id)
            .where(QuestionAsk.user_id == user_id)
            .order_by(QuestionAsk.created_at.desc(), QuestionAsk.id.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()

    return [(ask, question) for ask, question in rows]


async def count_for_user(
    db: AsyncSession,
    user_id: int,
) -> int:
    return (
        await db.scalar(
            select(func.count(QuestionAsk.id)).where(QuestionAsk.user_id == user_id)
        )
    ) or 0
