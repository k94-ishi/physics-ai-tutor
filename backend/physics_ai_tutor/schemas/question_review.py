from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, model_validator

from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import AnswerText, QuestionText


class QuestionReviewAction(StrEnum):
    APPROVE = "APPROVE"
    EDIT_APPROVE = "EDIT_APPROVE"
    REJECT = "REJECT"


class QuestionReviewReason(StrEnum):
    """Why an answer was rejected or needed editing.

    Stored as plain strings in SQL so codes can evolve without migrations.
    """

    PHYSICS_ERROR = "PHYSICS_ERROR"
    MATH_ERROR = "MATH_ERROR"
    INCOMPLETE = "INCOMPLETE"
    OFF_TOPIC = "OFF_TOPIC"
    TOO_ADVANCED = "TOO_ADVANCED"
    UNCLEAR = "UNCLEAR"
    FORMATTING = "FORMATTING"
    LANGUAGE = "LANGUAGE"
    DUPLICATE = "DUPLICATE"
    OTHER = "OTHER"


class QuestionReviewCreate(BaseModel):
    action: QuestionReviewAction
    # Language the reviewer read or edited; defaults to the original.
    language: Language | None = None
    question: QuestionText | None = None
    answer: AnswerText | None = None
    reason: QuestionReviewReason | None = None
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

    @model_validator(mode="after")
    def _require_reason(self) -> "QuestionReviewCreate":
        return validate_reason(self)


def validate_reason(review):
    """Rejects and edits must be labelled; OTHER must be explained."""
    needs_reason = (
        QuestionReviewAction.REJECT,
        QuestionReviewAction.EDIT_APPROVE,
    )
    if review.action in needs_reason and review.reason is None:
        raise ValueError(f"reason is required when action is {review.action}")

    if review.reason == QuestionReviewReason.OTHER and not (
        review.comment and review.comment.strip()
    ):
        raise ValueError("comment is required when reason is OTHER")

    return review


class ReviewerKind(StrEnum):
    HUMAN = "human"
    AI = "ai"
    POLICY = "policy"


class QuestionReviewResponse(BaseModel):
    id: int
    question_id: int
    action: QuestionReviewAction
    reviewer_kind: ReviewerKind
    policy_name: str | None
    language: Language
    reason: QuestionReviewReason | None
    before_question: str | None
    before_answer: str | None
    after_question: str | None
    after_answer: str | None
    reviewer_id: int | None
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
