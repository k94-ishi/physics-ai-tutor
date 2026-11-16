"""The async engine, session and transaction helper ([69]).

The sync equivalents are covered by the rest of the suite; these pin the
guarantees the async variant has to match before any slice relies on it.
"""

import logging

import pytest
from sqlalchemy import select, text

from physics_ai_tutor.database import database
from physics_ai_tutor.database import session as session_module
from physics_ai_tutor.database.transaction import async_transaction
from physics_ai_tutor.models import User

pytestmark = pytest.mark.anyio


async def test_async_session_reaches_the_database(async_db):
    result = await async_db.execute(text("SELECT 1"))

    assert result.scalar() == 1


async def test_async_transaction_commits_on_success(async_db):
    async with async_transaction(async_db, "test_commit"):
        async_db.add(User(email="async@example.com", hashed_password="x", role="user"))

    # A second session only sees it if the first one really committed.
    async with session_module.async_background_session() as other:
        found = await other.scalar(
            select(User).where(User.email == "async@example.com")
        )

    assert found is not None


async def test_async_transaction_rolls_back_and_reraises(async_db, caplog):
    with caplog.at_level(logging.WARNING):
        with pytest.raises(RuntimeError):
            async with async_transaction(async_db, "test_rollback"):
                async_db.add(
                    User(email="doomed@example.com", hashed_password="x", role="user")
                )
                await async_db.flush()
                raise RuntimeError("boom")

    assert "Rolling back transaction: operation=test_rollback" in caplog.text

    async with session_module.async_background_session() as other:
        found = await other.scalar(
            select(User).where(User.email == "doomed@example.com")
        )

    assert found is None


async def test_async_background_session_is_usable_and_closed():
    async with session_module.async_background_session() as db:
        assert await db.scalar(text("SELECT 1")) == 1

    # Exiting the context must have returned the connection to the pool.
    assert not db.in_transaction()


async def test_attributes_are_readable_after_commit(async_db):
    """`expire_on_commit=False`: a service may return an object it saved."""
    user = User(email="kept@example.com", hashed_password="x", role="user")

    async with async_transaction(async_db, "test_expire"):
        async_db.add(user)

    # Without expire_on_commit=False this raises: it would need an await.
    assert user.email == "kept@example.com"
    assert user.id is not None


def test_the_app_has_one_engine_and_it_is_async():
    """One engine, one pool at runtime ([110])."""
    assert database.async_engine.dialect.is_async
    for sync_name in ("engine", "SessionLocal"):
        assert not hasattr(database, sync_name), sync_name


def test_the_pool_is_sized_explicitly():
    pool = database.async_engine.pool
    assert pool.size() == database.POOL_SIZE
    assert pool._max_overflow == database.MAX_OVERFLOW
