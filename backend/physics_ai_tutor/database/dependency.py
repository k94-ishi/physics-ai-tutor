from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.database.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession]:
    """The request-scoped session every route depends on ([69], [110])."""
    async with AsyncSessionLocal() as db:
        yield db
