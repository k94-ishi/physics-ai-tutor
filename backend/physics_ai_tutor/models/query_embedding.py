from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class QueryEmbedding(Base):
    """Cached embedding of a search query ([49]).

    Keyed by (hash of the normalised text, embedding model): embeddings
    are only comparable within one model, so a model upgrade misses the
    cache instead of silently mixing incompatible vectors into results.
    The owner approved storing the vectors (2026-11-02); the normalised
    text is kept for inspection and adds no privacy surface beyond the
    already-recorded asks.
    """

    __tablename__ = "query_embeddings"
    __table_args__ = (
        UniqueConstraint("text_hash", "model", name="uq_query_embeddings_hash_model"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # sha256 of the normalised query text.
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # For an eviction CLI if the table ever grows enough to matter.
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
