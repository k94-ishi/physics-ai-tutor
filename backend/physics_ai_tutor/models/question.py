from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base
from physics_ai_tutor.schemas.language import Language


class Question(Base):
    """One physics Q&A unit, with its text in each supported language.

    `status` certifies the physics content and applies to every language
    column; a translation inherits the review of the original.
    """

    __allow_unmapped__ = True
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "question_ja IS NOT NULL OR question_en IS NOT NULL",
            name="questions_has_text",
        ),
        CheckConstraint(
            "(question_ja IS NULL) = (answer_ja IS NULL)",
            name="questions_ja_pair",
        ),
        CheckConstraint(
            "(question_en IS NULL) = (answer_en IS NULL)",
            name="questions_en_pair",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    question_ja: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_ja: Mapped[str | None] = mapped_column(Text, nullable=True)
    ja_provenance: Mapped[str | None] = mapped_column(String(10), nullable=True)

    question_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    en_provenance: Mapped[str | None] = mapped_column(String(10), nullable=True)

    original_language: Mapped[str] = mapped_column(
        String(10),
        server_default="ja",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        server_default="APPROVED",
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(20),
        server_default="MANUAL",
        nullable=False,
    )
    # Generation metadata; NULL for manual and imported rows. `prompt_version`
    # tracks prompts.ANSWER_PROMPT_VERSION at generation time.
    generation_model: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    generation_mode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    retrieved_question_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        server_default="{}",
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

    # Transient, populated by question_service before response
    # serialization; not mapped/persisted columns.
    concepts: list[str]
    retrieved_questions: list[dict[str, int | str]]
    generation: object | None
    ai_review: object | None

    # --- resolved text (transient) ----------------------------------------
    #
    # `question`, `answer`, `language` and `provenance` expose the text in
    # one language. `resolve(lang)` picks it; until then they fall back to
    # the original language so code that only reads `.question` keeps
    # working.

    def resolve(self, language: Language | str) -> None:
        lang = Language(language)
        served = lang if self.has(lang) else Language(self.original_language)
        self.__dict__["_resolved_language"] = served.value

    def _served_language(self) -> str:
        return self.__dict__.get("_resolved_language") or self.original_language

    @property
    def language(self) -> str:
        return self._served_language()

    @property
    def question(self) -> str:
        text = self.text(self._served_language()) or self.original_text()
        return text[0]

    @property
    def answer(self) -> str:
        text = self.text(self._served_language()) or self.original_text()
        return text[1]

    @property
    def provenance(self) -> str | None:
        return self.provenance_of(self._served_language())

    @property
    def available_languages(self) -> list[str]:
        return [lang.value for lang in Language if self.has(lang)]

    @property
    def texts(self) -> dict[str, dict[str, str | None]]:
        result: dict[str, dict[str, str | None]] = {}
        for lang in Language:
            text = self.text(lang)
            if text is not None:
                result[lang.value] = {
                    "question": text[0],
                    "answer": text[1],
                    "provenance": self.provenance_of(lang),
                }
        return result

    # --- language helpers -------------------------------------------------

    def text(self, language: Language | str) -> tuple[str, str] | None:
        lang = Language(language)
        question = getattr(self, f"question_{lang}")
        answer = getattr(self, f"answer_{lang}")

        if question is None or answer is None:
            return None

        return question, answer

    def provenance_of(self, language: Language | str) -> str | None:
        return getattr(self, f"{Language(language)}_provenance")

    def has(self, language: Language | str) -> bool:
        return self.text(language) is not None

    def set_text(
        self,
        language: Language | str,
        question: str,
        answer: str,
        provenance: str,
    ) -> None:
        lang = Language(language)
        setattr(self, f"question_{lang}", question)
        setattr(self, f"answer_{lang}", answer)
        setattr(self, f"{lang}_provenance", provenance)

    def original_text(self) -> tuple[str, str]:
        text = self.text(self.original_language)

        if text is None:
            # Fall back to whichever language exists; the DB constraint
            # guarantees at least one.
            for lang in Language:
                text = self.text(lang)
                if text is not None:
                    break

        assert text is not None
        return text
