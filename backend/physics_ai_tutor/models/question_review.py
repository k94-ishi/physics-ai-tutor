from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class QuestionReview(Base):
    __tablename__ = "question_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    # Why the answer was rejected or edited; NULL for plain approvals.
    reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Language of the text the reviewer looked at or edited.
    language: Mapped[str] = mapped_column(
        String(10), server_default="ja", nullable=False
    )
    before_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Who produced this row: a human admin, the AI reviewer, or a policy
    # acting on the AI reviewer's verdict (then `policy_name` says which).
    reviewer_kind: Mapped[str] = mapped_column(
        String(10), server_default="human", nullable=False
    )
    policy_name: Mapped[str | None] = mapped_column(String, nullable=True)
    # Kept after the reviewer account is deleted so the audit trail survives.
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
