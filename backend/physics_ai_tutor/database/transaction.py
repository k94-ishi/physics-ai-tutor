"""The one place that commits or rolls back an application session ([59]).

Two variants, one contract: commit when the block succeeds; roll back,
log and re-raise otherwise. Use `transaction` from sync code and
`async_transaction` from converted code ([69]); nothing else in the
application may call `commit()` or `rollback()`, which
`tests/test_architecture.py` enforces.
"""

import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@contextmanager
def transaction(db: Session, operation: str) -> Iterator[None]:
    """Commit when the block succeeds; roll back, log and re-raise otherwise."""
    try:
        yield
        db.commit()
    except Exception:
        logger.warning("Rolling back transaction: operation=%s", operation)
        db.rollback()
        raise


@asynccontextmanager
async def async_transaction(db: AsyncSession, operation: str) -> AsyncIterator[None]:
    """As `transaction`, on an `AsyncSession`."""
    try:
        yield
        await db.commit()
    except Exception:
        logger.warning("Rolling back transaction: operation=%s", operation)
        await db.rollback()
        raise
