import logging
import random

from sqlalchemy.orm import Session

from physics_ai_tutor.core.exceptions import RateLimitExceeded
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
    try:
        rate_limit_repository.record_hit(db, action, bucket_key)

        if random.random() < CLEANUP_PROBABILITY:
            deleted = rate_limit_repository.delete_hits_older_than(
                db, MAX_WINDOW_SECONDS
            )
            if deleted:
                logger.info("Pruned expired rate-limit hits: count=%d", deleted)

        db.commit()
    except Exception:
        db.rollback()
        raise
