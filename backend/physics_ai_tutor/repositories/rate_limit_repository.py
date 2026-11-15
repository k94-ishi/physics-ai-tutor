from datetime import timedelta
from typing import cast

from sqlalchemy import CursorResult, func, select
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.models.rate_limit_hit import RateLimitHit


def _count_select(action: str, bucket_key: str, window_seconds: int):
    # Compare against the database clock so check and record agree on time.
    cutoff = func.now() - timedelta(seconds=window_seconds)

    return select(func.count(RateLimitHit.id)).where(
        RateLimitHit.action == action,
        RateLimitHit.bucket_key == bucket_key,
        RateLimitHit.created_at > cutoff,
    )


async def async_count_recent_hits(
    db: AsyncSession,
    action: str,
    bucket_key: str,
    window_seconds: int,
) -> int:
    return (await db.scalar(_count_select(action, bucket_key, window_seconds))) or 0


async def async_record_hit(
    db: AsyncSession,
    action: str,
    bucket_key: str,
) -> RateLimitHit:
    hit = RateLimitHit(action=action, bucket_key=bucket_key)
    db.add(hit)
    await db.flush()

    return hit


def _delete_old_statement(max_age_seconds: int):
    cutoff = func.now() - timedelta(seconds=max_age_seconds)

    return sql_delete(RateLimitHit).where(RateLimitHit.created_at < cutoff)


async def async_delete_hits_older_than(
    db: AsyncSession,
    max_age_seconds: int,
) -> int:
    result = cast(
        CursorResult, await db.execute(_delete_old_statement(max_age_seconds))
    )
    deleted = result.rowcount
    await db.flush()

    return deleted
