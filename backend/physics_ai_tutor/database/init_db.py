import asyncio

from physics_ai_tutor.database.base import Base
from physics_ai_tutor.database.database import async_engine


async def _create_all() -> None:
    """Async since [109]: the app keeps one engine."""
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def init_db():
    asyncio.run(_create_all())


if __name__ == "__main__":
    init_db()
