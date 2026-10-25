from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ja: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    name_en: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    extraction_model: Mapped[str] = mapped_column(String, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    extraction_prompt_version: Mapped[str] = mapped_column(String, nullable=False)
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

    def name_in(self, language: str) -> str | None:
        return self.name_ja if language == "ja" else self.name_en

    def display_name(self, language: str) -> str:
        # Prefer the requested language, fall back to the other.
        name = self.name_in(language)
        if name is None:
            name = self.name_en if language == "ja" else self.name_ja
        assert name is not None
        return name

    @property
    def name(self) -> str:
        # Legacy accessor: Japanese name first, English otherwise.
        return self.display_name("ja")
