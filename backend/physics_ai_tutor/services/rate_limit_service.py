import logging
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.core.exceptions import RateLimitExceeded
from physics_ai_tutor.database.transaction import async_transaction, transaction
from physics_ai_tutor.repositories import rate_limit_repository

logger = logging.getLogger(__name__)

# No limit uses a window longer than a day, so older rows are dead weight.
MAX_WINDOW_SECONDS = 86400

# Prune expired rows on roughly 1% of record calls.
CLEANUP_PROBABILITY = 0.01


def check(
    db: Session,
    action: str,
    bucket_key: str,
    limits: list[tuple[int, int]],
) -> None:
    """limits: [(max_requests, window_seconds), ...].

    Raises RateLimitExceeded if any window's limit is already reached.
    Read-only; callers consume quota separately via record().
    """
    for max_requests, window_seconds in limits:
        hits = rate_limit_repository.count_recent_hits(
            db, action, bucket_key, window_seconds
        )

        if hits >= max_requests:
            raise RateLimitExceeded(f"{action}:{bucket_key}")


def record(
    db: Session,
    action: str,
    bucket_key: str,
) -> None:
    """Count one request against the bucket and commit immediately.

    The commit must not wait for the rest of the request: a later failure
    (e.g. a DeepSeek error) should not hand the quota back.
    """
    with transaction(db, "record_rate_limit_hit"):
        rate_limit_repository.record_hit(db, action, bucket_key)

        if random.random() < CLEANUP_PROBABILITY:
            deleted = rate_limit_repository.delete_hits_older_than(
                db, MAX_WINDOW_SECONDS
            )
            if deleted:
                logger.info("Pruned expired rate-limit hits: count=%d", deleted)


async def async_check(
    db: AsyncSession,
    action: str,
    bucket_key: str,
    limits: list[tuple[int, int]],
) -> None:
    """As `check`, on the event loop ([70])."""
    for max_requests, window_seconds in limits:
        hits = await rate_limit_repository.async_count_recent_hits(
            db, action, bucket_key, window_seconds
        )

        if hits >= max_requests:
            raise RateLimitExceeded(f"{action}:{bucket_key}")


async def async_record(
    db: AsyncSession,
    action: str,
    bucket_key: str,
) -> None:
    """As `record`, on the event loop ([70])."""
    async with async_transaction(db, "record_rate_limit_hit"):
        await rate_limit_repository.async_record_hit(db, action, bucket_key)

        if random.random() < CLEANUP_PROBABILITY:
            deleted = await rate_limit_repository.async_delete_hits_older_than(
                db, MAX_WINDOW_SECONDS
            )
            if deleted:
                logger.info("Pruned expired rate-limit hits: count=%d", deleted)
