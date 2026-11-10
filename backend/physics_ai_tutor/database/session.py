"""Sessions for work that outlives a request (background tasks) ([59])."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from physics_ai_tutor.database.database import SessionLocal


@contextmanager
def background_session() -> Iterator[Session]:
    """A fresh session that is always closed; requests use `get_db` instead."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
