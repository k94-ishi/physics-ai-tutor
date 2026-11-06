from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
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
    """Record a cache hit; best effort, never blocks the search."""
    row.hit_count += 1
    row.last_used_at = func.now()
    db.commit()


def create(
    db: Session,
    text_hash: str,
    normalized_text: str,
    model: str,
    embedding: list[float],
) -> QueryEmbedding:
    """Insert, or return the row a concurrent request inserted first."""
    row = QueryEmbedding(
        text_hash=text_hash,
        normalized_text=normalized_text,
        model=model,
        embedding=embedding,
    )
    db.add(row)

    try:
        db.commit()
    except IntegrityError:
        # Two identical searches raced; the other one won and that is fine.
        db.rollback()
        existing = get(db, text_hash, model)
        assert existing is not None
        return existing

    return row
