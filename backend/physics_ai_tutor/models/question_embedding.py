from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class QuestionEmbedding(Base):
    __tablename__ = "question_embeddings"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    
    question_id: Mapped[int] = mapped_column(
        ForeignKey(
            "questions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False
    )
    
    model: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
