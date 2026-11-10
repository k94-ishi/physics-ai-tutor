"""Liveness checks behind the health endpoints."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def check_database(db: Session) -> None:
    """Run a trivial query; raises if the database is unreachable."""
    db.execute(text("SELECT 1"))
