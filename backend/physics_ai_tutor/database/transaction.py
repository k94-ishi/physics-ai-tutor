"""The one place that commits or rolls back an application session ([59]).

Commit when the block succeeds; roll back, log and re-raise otherwise.
Nothing else in the application may call `commit()` or `rollback()`,
which `tests/test_architecture.py` enforces. Async only since [110].
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@asynccontextmanager
async def async_transaction(db: AsyncSession, operation: str) -> AsyncIterator[None]:
    """Commit when the block succeeds; roll back, log and re-raise otherwise."""
    try:
        yield
        await db.commit()
    except Exception:
        logger.warning("Rolling back transaction: operation=%s", operation)
        await db.rollback()
        raise
