from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.models import QueryEmbedding


def _by_hash(text_hash: str, model: str):
    """The lookup both variants run."""
    return select(QueryEmbedding).where(
        QueryEmbedding.text_hash == text_hash,
        QueryEmbedding.model == model,
    )


def get(db: Session, text_hash: str, model: str) -> QueryEmbedding | None:
    return db.scalars(_by_hash(text_hash, model)).first()


async def async_get(
    db: AsyncSession, text_hash: str, model: str
) -> QueryEmbedding | None:
    return (await db.scalars(_by_hash(text_hash, model))).first()


def touch(db: Session, row: QueryEmbedding) -> None:
    """Record a cache hit on the row (the caller commits)."""
    row.hit_count += 1
    row.last_used_at = func.now()
    db.flush()


async def async_touch(db: AsyncSession, row: QueryEmbedding) -> None:
    """Record a cache hit on the row (the caller commits)."""
    row.hit_count += 1
    row.last_used_at = func.now()
    await db.flush()


def _new_row(
    text_hash: str, normalized_text: str, model: str, embedding: list[float]
) -> QueryEmbedding:
    return QueryEmbedding(
        text_hash=text_hash,
        normalized_text=normalized_text,
        model=model,
        embedding=embedding,
    )


def create(
    db: Session,
    text_hash: str,
    normalized_text: str,
    model: str,
    embedding: list[float],
) -> QueryEmbedding:
    """Insert a cached query embedding (the caller commits)."""
    row = _new_row(text_hash, normalized_text, model, embedding)
    db.add(row)
    db.flush()
    return row


async def async_create(
    db: AsyncSession,
    text_hash: str,
    normalized_text: str,
    model: str,
    embedding: list[float],
) -> QueryEmbedding:
    """Insert a cached query embedding (the caller commits)."""
    row = _new_row(text_hash, normalized_text, model, embedding)
    db.add(row)
    await db.flush()
    return row
