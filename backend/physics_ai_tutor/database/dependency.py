from collections.abc import AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.database.database import AsyncSessionLocal, SessionLocal


def get_db() -> Generator[Session]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession]:
    """The async counterpart of `get_db`, for converted routes ([69])."""
    async with AsyncSessionLocal() as db:
        yield db
