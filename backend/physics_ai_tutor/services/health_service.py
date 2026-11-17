"""Liveness checks behind the health endpoints."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_database(db: AsyncSession) -> None:
    """Run a trivial query; raises if the database is unreachable."""
    await db.execute(text("SELECT 1"))
