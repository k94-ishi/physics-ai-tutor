from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class ConceptTerm(Base):
    """One word for a concept sense in one language ([55]).

    A sense may have many terms per language, and the same word may belong
    to several senses (位相 = phase / topology), so `(language, normalized)`
    is indexed but deliberately not unique.
    """

    __tablename__ = "concept_terms"
    __table_args__ = (
        UniqueConstraint(
            "concept_id", "language", "normalized", name="uq_concept_terms_sense_word"
        ),
        Index("ix_concept_terms_lookup", "language", "normalized"),
        Index(
            "uq_concept_terms_one_preferred",
            "concept_id",
            "language",
            unique=True,
            postgresql_where=text("is_preferred"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    is_preferred: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # EXTRACTED (concept extraction), MACHINE (translator), TEACHER (admin).
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="EXTRACTED"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
