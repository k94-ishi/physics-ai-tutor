from datetime import date, datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from physics_ai_tutor.models import Question, QuestionAsk, RateLimitHit

AI_SOURCES = ["AI_GENERATED", "RAG_RESULT"]


def generations_per_day(db: Session, since: datetime) -> dict[date, int]:
    day = func.date_trunc("day", Question.created_at)

    rows = (
        db.query(day, func.count(Question.id))
        .filter(Question.source.in_(AI_SOURCES), Question.created_at >= since)
        .group_by(day)
        .all()
    )

    return {row_day.date(): count for row_day, count in rows}


def asks_per_day(db: Session, since: datetime) -> dict[date, tuple[int, int, int]]:
    """day -> (asks, cache_hits, distinct_users) for signed-in asks."""
    day = func.date_trunc("day", QuestionAsk.created_at)
    cache_hit = case((QuestionAsk.cache_hit, 1), else_=0)

    rows = (
        db.query(
            day,
            func.count(QuestionAsk.id),
            func.coalesce(func.sum(cache_hit), 0),
            func.count(func.distinct(QuestionAsk.user_id)),
        )
        .filter(QuestionAsk.created_at >= since)
        .group_by(day)
        .all()
    )

    return {
        row_day.date(): (asks, int(hits), users) for row_day, asks, hits, users in rows
    }


def unreviewed_backlog(db: Session) -> tuple[int, float | None]:
    """(count, median age in days) of UNREVIEWED questions."""
    count = (
        db.query(func.count(Question.id))
        .filter(Question.status == "UNREVIEWED")
        .scalar()
    ) or 0

    age_days = func.extract("epoch", func.now() - Question.created_at) / 86400.0
    median = (
        db.query(func.percentile_cont(0.5).within_group(age_days.asc()))
        .filter(Question.status == "UNREVIEWED")
        .scalar()
    )

    return count, float(median) if median is not None else None


def anonymous_ip_buckets_since(db: Session, since: timedelta) -> int:
    return (
        db.query(func.count(func.distinct(RateLimitHit.bucket_key)))
        .filter(
            RateLimitHit.action == "ai_ask",
            RateLimitHit.bucket_key.like("ip:%"),
            RateLimitHit.created_at > func.now() - since,
        )
        .scalar()
    ) or 0
