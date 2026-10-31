from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class AiReviewRun(Base):
    """One invocation of the AI reviewer over a set of questions.

    The eligible question ids are fixed at start time so the run is
    deterministic and progress (reviewed/failed counts, updated as it goes)
    can be polled. A partial unique index allows only one 'running' row.
    """

    __tablename__ = "ai_review_runs"
    __table_args__ = (
        Index(
            "uq_ai_review_runs_single_running",
            "status",
            unique=True,
            postgresql_where="status = 'running'",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # scheduled | manual | cli
    trigger: Mapped[str] = mapped_column(String(10), nullable=False)
    # pending | stale | selected
    scope: Mapped[str] = mapped_column(String(10), nullable=False)
    started_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    question_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), server_default="{}", nullable=False
    )
    requested_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    reviewed_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    # running | done | failed | cancelled
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
