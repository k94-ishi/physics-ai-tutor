from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from physics_ai_tutor.models.rate_limit_hit import RateLimitHit


def count_recent_hits(
    db: Session,
    action: str,
    bucket_key: str,
    window_seconds: int,
) -> int:
    # Compare against the database clock so check and record agree on time.
    cutoff = func.now() - timedelta(seconds=window_seconds)

    return (
        db.query(func.count(RateLimitHit.id))
        .filter(
            RateLimitHit.action == action,
            RateLimitHit.bucket_key == bucket_key,
            RateLimitHit.created_at > cutoff,
        )
        .scalar()
    ) or 0


def record_hit(
    db: Session,
    action: str,
    bucket_key: str,
) -> RateLimitHit:
    hit = RateLimitHit(action=action, bucket_key=bucket_key)
    db.add(hit)
    db.flush()

    return hit


def delete_hits_older_than(
    db: Session,
    max_age_seconds: int,
) -> int:
    cutoff = func.now() - timedelta(seconds=max_age_seconds)

    deleted = (
        db.query(RateLimitHit)
        .filter(RateLimitHit.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.flush()

    return deleted
