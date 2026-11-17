from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class BackgroundClaim(Base):
    """One piece of background work a worker has taken ([75]).

    Background de-duplication used to be a set inside the process, which
    only holds for one worker: two would translate the same row twice.
    The unique `(kind, key)` is the real guard - a claim is an insert that
    exactly one worker can win.

    A dedicated table rather than a `translation_claimed_at` column on
    `questions` and another on `concepts`: one mechanism for every kind of
    claim, and the content tables stay free of operational bookkeeping.

    Rows are transient. A claim outlives its worker only until the
    timeout, after which another worker may take it over, so a crash
    cannot park a row forever.
    """

    __tablename__ = "background_claims"
    __table_args__ = (
        UniqueConstraint("kind", "key", name="uq_background_claims_work"),
        Index("ix_background_claims_claimed_at", "claimed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # What sort of work, e.g. "translate_question".
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    # The row the work is about; a question id or a concept id.
    key: Mapped[int] = mapped_column(Integer, nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
