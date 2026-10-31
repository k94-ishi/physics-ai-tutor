from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question_review import QuestionReviewReason


class AiReviewVerdict(StrEnum):
    APPROVE = "APPROVE"
    EDIT = "EDIT"
    REJECT = "REJECT"


class AiReviewCreate(BaseModel):
    """What the AI reviewer stores for one graded answer ([13] fills it)."""

    question_id: int
    language: Language
    # None when the model output could not be parsed.
    verdict: AiReviewVerdict | None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reasons: list[QuestionReviewReason] = Field(default_factory=list)
    rationale: str | None = None
    suggested_answer: str | None = None
    rubric: dict[str, int] | None = None
    model: str
    prompt_version: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class AiReviewResponse(BaseModel):
    id: int
    question_id: int
    language: Language
    verdict: AiReviewVerdict | None
    confidence: float | None
    reasons: list[str]
    rationale: str | None
    suggested_answer: str | None
    rubric: dict[str, int] | None
    model: str
    prompt_version: str
    prompt_tokens: int | None
    completion_tokens: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
