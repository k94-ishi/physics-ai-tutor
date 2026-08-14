from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class QuestionConcept(Base):
    __tablename__ = "question_concepts"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
    )
