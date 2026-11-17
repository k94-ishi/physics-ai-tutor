from datetime import date, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.models import Question, QuestionAsk, RateLimitHit

AI_SOURCES = ["AI_GENERATED", "RAG_RESULT"]


async def generations_per_day(db: AsyncSession, since: datetime) -> dict[date, int]:
    day = func.date_trunc("day", Question.created_at)

    query = (
        select(day, func.count(Question.id))
        .where(Question.source.in_(AI_SOURCES), Question.created_at >= since)
        .group_by(day)
    )
    rows = (await db.execute(query)).all()

    return {row_day.date(): count for row_day, count in rows}


async def asks_per_day(
    db: AsyncSession, since: datetime
) -> dict[date, tuple[int, int, int]]:
    """day -> (asks, cache_hits, distinct_users) for signed-in asks."""
    day = func.date_trunc("day", QuestionAsk.created_at)
    cache_hit = case((QuestionAsk.cache_hit, 1), else_=0)

    query = (
        select(
            day,
            func.count(QuestionAsk.id),
            func.coalesce(func.sum(cache_hit), 0),
            func.count(func.distinct(QuestionAsk.user_id)),
        )
        .where(QuestionAsk.created_at >= since)
        .group_by(day)
    )
    rows = (await db.execute(query)).all()

    return {
        row_day.date(): (asks, int(hits), users) for row_day, asks, hits, users in rows
    }


async def unreviewed_backlog(db: AsyncSession) -> tuple[int, float | None]:
    """(count, median age in days) of UNREVIEWED questions."""
    count = (
        await db.scalar(
            select(func.count(Question.id)).where(Question.status == "UNREVIEWED")
        )
    ) or 0

    age_days = func.extract("epoch", func.now() - Question.created_at) / 86400.0
    median = await db.scalar(
        select(func.percentile_cont(0.5).within_group(age_days.asc())).where(
            Question.status == "UNREVIEWED"
        )
    )

    return count, float(median) if median is not None else None


async def anonymous_ip_buckets_since(db: AsyncSession, since: timedelta) -> int:
    query = select(func.count(func.distinct(RateLimitHit.bucket_key))).where(
        RateLimitHit.action == "ai_ask",
        RateLimitHit.bucket_key.like("ip:%"),
        RateLimitHit.created_at > func.now() - since,
    )

    return (await db.scalar(query)) or 0
