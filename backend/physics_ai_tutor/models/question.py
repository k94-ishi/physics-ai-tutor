from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
