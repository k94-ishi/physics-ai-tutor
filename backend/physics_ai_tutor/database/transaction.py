"""The one place that commits or rolls back an application session ([59])."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

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
