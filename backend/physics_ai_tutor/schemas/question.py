from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from physics_ai_tutor.schemas.language import Language, TextProvenance

QuestionText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]
AnswerText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]


class QuestionStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class QuestionSource(StrEnum):
    MANUAL = "MANUAL"
    AI_GENERATED = "AI_GENERATED"
    RAG_RESULT = "RAG_RESULT"


class LocalizedText(BaseModel):
    question: str
    answer: str
    provenance: TextProvenance | None = None

    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    """Text for one or both languages.

    Accepts the legacy shape `{question, answer, language?}` (language
    defaults to ja) or the explicit shape with `question_ja`, `answer_ja`,
    `question_en`, `answer_en`. At least one complete pair is required.
    """

    question: QuestionText | None = None
    answer: AnswerText | None = None
    language: Language = Language.JA

    question_ja: QuestionText | None = None
    answer_ja: AnswerText | None = None
    question_en: QuestionText | None = None
    answer_en: AnswerText | None = None

    @model_validator(mode="after")
    def _normalise(self) -> "QuestionCreate":
        if self.question is not None or self.answer is not None:
            if self.question is None or self.answer is None:
                raise ValueError("question and answer must be given together")
            if getattr(self, f"question_{self.language}") is not None:
                raise ValueError(
                    f"Give either question/answer or question_{self.language}, not both"
                )
            setattr(self, f"question_{self.language}", self.question)
            setattr(self, f"answer_{self.language}", self.answer)

        for lang in Language:
            q = getattr(self, f"question_{lang}")
            a = getattr(self, f"answer_{lang}")
            if (q is None) != (a is None):
                raise ValueError(f"question_{lang} and answer_{lang} go together")

        if not self.texts():
            raise ValueError("At least one language's question and answer is required")

        return self

    def texts(self) -> dict[Language, tuple[str, str]]:
        result: dict[Language, tuple[str, str]] = {}
        for lang in Language:
            q = getattr(self, f"question_{lang}")
            a = getattr(self, f"answer_{lang}")
            if q is not None and a is not None:
                result[lang] = (q, a)
        return result

    def original_language(self) -> Language:
        # The language given via the legacy fields, or the first present one.
        if self.question is not None:
            return self.language
        return next(iter(self.texts()))


class QuestionUpdate(QuestionCreate):
    pass


class QuestionRefSummary(BaseModel):
    id: int
    question: str

    model_config = {"from_attributes": True}


class QuestionResponse(BaseModel):
    id: int
    # Text resolved to the requested language (falls back to the original).
    question: str
    answer: str
    language: Language
    provenance: TextProvenance | None = None
    original_language: Language
    available_languages: list[Language] = Field(default_factory=list)
    texts: dict[Language, LocalizedText] = Field(default_factory=dict)
    status: QuestionStatus
    source: QuestionSource
    concepts: list[str] = Field(default_factory=list)
    retrieved_questions: list[QuestionRefSummary] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class QuestionListResponse(BaseModel):
    items: list[QuestionResponse]
    total: int
    page: int
    size: int


class QuestionImportResponse(BaseModel):
    created_count: int
    questions: list[QuestionResponse]


class TranslationResult(BaseModel):
    question_id: int
    success: bool
    language: Language | None = None


class TranslationBatchResponse(BaseModel):
    results: list[TranslationResult]
