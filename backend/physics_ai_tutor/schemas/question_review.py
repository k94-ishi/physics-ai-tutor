from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, model_validator

from physics_ai_tutor.schemas.question import AnswerText, QuestionText


class QuestionReviewAction(StrEnum):
    APPROVE = "APPROVE"
    EDIT_APPROVE = "EDIT_APPROVE"
    REJECT = "REJECT"


class QuestionReviewCreate(BaseModel):
    action: QuestionReviewAction
    question: QuestionText | None = None
    answer: AnswerText | None = None
    comment: str | None = None

    @model_validator(mode="after")
    def _require_content_for_edit_approve(self) -> "QuestionReviewCreate":
        if self.action == QuestionReviewAction.EDIT_APPROVE and (
            self.question is None or self.answer is None
        ):
            raise ValueError(
                "question and answer are required when action is EDIT_APPROVE"
            )
        return self


class QuestionReviewResponse(BaseModel):
    id: int
    question_id: int
    action: QuestionReviewAction
    before_question: str | None
    before_answer: str | None
    after_question: str | None
    after_answer: str | None
    reviewer_id: int
    comment: str | None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
