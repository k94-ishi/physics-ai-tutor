from sqlalchemy import func
from sqlalchemy.orm import Session

from physics_ai_tutor.models import QueryEmbedding


def get(db: Session, text_hash: str, model: str) -> QueryEmbedding | None:
    return (
        db.query(QueryEmbedding)
        .filter(
            QueryEmbedding.text_hash == text_hash,
            QueryEmbedding.model == model,
        )
        .first()
    )


def touch(db: Session, row: QueryEmbedding) -> None:
    """Record a cache hit on the row (the caller commits)."""
    row.hit_count += 1
    row.last_used_at = func.now()
    db.flush()


def create(
    db: Session,
    text_hash: str,
    normalized_text: str,
    model: str,
    embedding: list[float],
) -> QueryEmbedding:
    """Insert a cached query embedding (the caller commits)."""
    row = QueryEmbedding(
        text_hash=text_hash,
        normalized_text=normalized_text,
        model=model,
        embedding=embedding,
    )
    db.add(row)
    db.flush()
    return row
