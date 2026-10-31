from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class RateLimitHit(Base):
    """One counted request for the sliding-window rate limiter.

    Stored in Postgres so counters survive restarts; rows older than the
    longest window are pruned opportunistically on record.
    """

    __tablename__ = "rate_limit_hits"
    __table_args__ = (
        Index("ix_rate_limit_hits_window", "action", "bucket_key", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    bucket_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
