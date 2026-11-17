"""Sessions for work that outlives a request (background tasks) ([59]).

Tests point this helper at the test database, so every background task
must open its session here rather than from a factory of its own.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.database.database import AsyncSessionLocal


@asynccontextmanager
async def background_session() -> AsyncIterator[AsyncSession]:
    """A fresh session that is always closed; requests use `get_db`."""
    async with AsyncSessionLocal() as db:
        yield db
