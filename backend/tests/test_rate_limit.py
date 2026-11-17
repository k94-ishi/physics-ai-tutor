from datetime import timedelta

import pytest
from sqlalchemy import func, select

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


# The limiter has one implementation since [107]; these test it directly.


@pytest.mark.anyio
async def test_count_recent_hits_scopes_by_action_bucket_and_window(async_db):
    async_db.add_all(
        [
            RateLimitHit(action="ai_ask", bucket_key="ip:1.2.3.4"),
            RateLimitHit(action="ai_ask", bucket_key="ip:5.6.7.8"),
            RateLimitHit(action="login", bucket_key="ip:1.2.3.4"),
            _old_hit("ai_ask", "ip:1.2.3.4", age_seconds=7200),
        ]
    )
    await async_db.flush()

    count = await rate_limit_repository.count_recent_hits(
        async_db, "ai_ask", "ip:1.2.3.4", 3600
    )

    assert count == 1


@pytest.mark.anyio
async def test_delete_hits_older_than_removes_only_expired_rows(async_db):
    fresh = RateLimitHit(action="ai_ask", bucket_key="ip:1.2.3.4")
    async_db.add_all([fresh, _old_hit("ai_ask", "ip:1.2.3.4", age_seconds=172800)])
    await async_db.flush()

    deleted = await rate_limit_repository.delete_hits_older_than(async_db, 86400)

    assert deleted == 1
    remaining = (await async_db.scalars(select(RateLimitHit.id))).all()
    assert remaining == [fresh.id]


@pytest.mark.anyio
async def test_check_raises_when_any_window_is_full(async_db):
    for _ in range(3):
        await rate_limit_repository.record_hit(async_db, "ai_ask", "ip:1.2.3.4")

    with pytest.raises(RateLimitExceeded):
        await rate_limit_service.check(
            async_db, "ai_ask", "ip:1.2.3.4", [(3, 3600), (10, 86400)]
        )


@pytest.mark.anyio
async def test_check_passes_below_every_limit(async_db):
    await rate_limit_repository.record_hit(async_db, "ai_ask", "ip:1.2.3.4")

    await rate_limit_service.check(
        async_db, "ai_ask", "ip:1.2.3.4", [(3, 3600), (10, 86400)]
    )


@pytest.mark.anyio
async def test_record_persists_hit_and_prunes_expired_rows(async_db, monkeypatch):
    async_db.add(_old_hit("ai_ask", "ip:1.2.3.4", age_seconds=172800))
    await async_db.flush()

    # Force the opportunistic cleanup branch to run.
    monkeypatch.setattr(rate_limit_service.random, "random", lambda: 0.0)

    await rate_limit_service.record(async_db, "ai_ask", "ip:1.2.3.4")

    hits = (await async_db.scalars(select(RateLimitHit))).all()
    assert len(hits) == 1
    recent = await rate_limit_repository.count_recent_hits(
        async_db, "ai_ask", "ip:1.2.3.4", 60
    )
    assert recent == 1
