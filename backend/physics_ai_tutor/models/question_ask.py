from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class QuestionAsk(Base):
    """One signed-in ask of a question, cache hit or fresh generation.

    A question can have many askers and an asker can repeat a question, so
    this is a table rather than a column on `questions`. Anonymous asks are
    not recorded. Deleting the account unlinks the rows (`SET NULL`) so the
    aggregate counts survive without personal data.
    """

    __tablename__ = "question_asks"
    __table_args__ = (Index("ix_question_asks_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Language the student asked in, not the row's original language.
    language: Mapped[str] = mapped_column(
        String(10), server_default="ja", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
