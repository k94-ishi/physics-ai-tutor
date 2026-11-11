"""Sessions for work that outlives a request (background tasks) ([59]).

Tests point these two helpers at the test database, so every background
task must open its session here rather than from a factory of its own.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.database.database import AsyncSessionLocal, SessionLocal


@contextmanager
def background_session() -> Iterator[Session]:
    """A fresh session that is always closed; requests use `get_db` instead."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def async_background_session() -> AsyncIterator[AsyncSession]:
    """As `background_session`, on an `AsyncSession` ([69])."""
    async with AsyncSessionLocal() as db:
        yield db
