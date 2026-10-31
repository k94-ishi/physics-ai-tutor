from datetime import timedelta

import pytest
from sqlalchemy import func

from physics_ai_tutor.core.exceptions import RateLimitExceeded
from physics_ai_tutor.models import RateLimitHit
from physics_ai_tutor.repositories import rate_limit_repository
from physics_ai_tutor.services import rate_limit_service


def _old_hit(action: str, bucket_key: str, age_seconds: int) -> RateLimitHit:
    # Backdate against the database clock, which the limiter compares to.
    return RateLimitHit(
        action=action,
        bucket_key=bucket_key,
        created_at=func.now() - timedelta(seconds=age_seconds),
    )


def test_count_recent_hits_scopes_by_action_bucket_and_window(db):
    db.add_all(
        [
            RateLimitHit(action="ai_ask", bucket_key="ip:1.2.3.4"),
            RateLimitHit(action="ai_ask", bucket_key="ip:5.6.7.8"),
            RateLimitHit(action="login", bucket_key="ip:1.2.3.4"),
            _old_hit("ai_ask", "ip:1.2.3.4", age_seconds=7200),
        ]
    )
    db.flush()

    count = rate_limit_repository.count_recent_hits(db, "ai_ask", "ip:1.2.3.4", 3600)

    assert count == 1


def test_delete_hits_older_than_removes_only_expired_rows(db):
    fresh = RateLimitHit(action="ai_ask", bucket_key="ip:1.2.3.4")
    db.add_all([fresh, _old_hit("ai_ask", "ip:1.2.3.4", age_seconds=172800)])
    db.flush()

    deleted = rate_limit_repository.delete_hits_older_than(db, 86400)

    assert deleted == 1
    assert db.query(RateLimitHit).one().id == fresh.id


def test_check_raises_when_any_window_is_full(db):
    for _ in range(3):
        rate_limit_repository.record_hit(db, "ai_ask", "ip:1.2.3.4")

    with pytest.raises(RateLimitExceeded):
        rate_limit_service.check(db, "ai_ask", "ip:1.2.3.4", [(3, 3600), (10, 86400)])


def test_check_passes_below_every_limit(db):
    rate_limit_repository.record_hit(db, "ai_ask", "ip:1.2.3.4")

    rate_limit_service.check(db, "ai_ask", "ip:1.2.3.4", [(3, 3600), (10, 86400)])


def test_record_persists_hit_and_prunes_expired_rows(db, monkeypatch):
    db.add(_old_hit("ai_ask", "ip:1.2.3.4", age_seconds=172800))
    db.flush()

    # Force the opportunistic cleanup branch to run.
    monkeypatch.setattr(rate_limit_service.random, "random", lambda: 0.0)

    rate_limit_service.record(db, "ai_ask", "ip:1.2.3.4")

    hits = db.query(RateLimitHit).all()
    assert len(hits) == 1
    assert rate_limit_repository.count_recent_hits(db, "ai_ask", "ip:1.2.3.4", 60) == 1
