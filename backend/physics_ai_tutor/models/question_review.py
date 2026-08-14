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
    before_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
