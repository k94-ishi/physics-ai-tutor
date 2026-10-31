from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class AiReview(Base):
    """An AI reviewer's verdict on a question, separate from human reviews.

    Advisory data only: nothing here changes a question's status. When a
    policy is later allowed to act, the status change is written to
    `question_reviews` with `reviewer_kind='policy'`, keeping the human
    audit trail unambiguous.
    """

    __tablename__ = "ai_reviews"
    __table_args__ = (
        Index("ix_ai_reviews_question_created", "question_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Language of the text that was graded.
    language: Mapped[str] = mapped_column(
        String(10), server_default="ja", nullable=False
    )
    # NULL when the model's output could not be parsed; the raw text is then
    # kept in `rationale` so failures stay visible.
    verdict: Mapped[str | None] = mapped_column(String(10), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Reason codes from the human review vocabulary (question_reviews.reason).
    reasons: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Per-criterion scores; JSONB so the rubric can evolve without migrations.
    rubric: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
