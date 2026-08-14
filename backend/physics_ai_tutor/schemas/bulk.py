from pydantic import BaseModel, Field, model_validator

from physics_ai_tutor.schemas.question import QuestionResponse
from physics_ai_tutor.schemas.question_review import QuestionReviewAction


class BulkDeleteRequest(BaseModel):
    question_ids: list[int] = Field(min_length=1, max_length=100)


class BulkDeleteResponse(BaseModel):
    deleted_count: int
    not_found_ids: list[int]


class BulkReviewRequest(BaseModel):
    question_ids: list[int] = Field(min_length=1, max_length=100)
    action: QuestionReviewAction
    comment: str | None = None

    @model_validator(mode="after")
    def _reject_edit_approve(self) -> "BulkReviewRequest":
        if self.action == QuestionReviewAction.EDIT_APPROVE:
            raise ValueError(
                "EDIT_APPROVE is not supported for bulk review; "
                "edit and approve questions individually instead."
            )
        return self


class BulkReviewResponse(BaseModel):
    questions: list[QuestionResponse]
    not_found_ids: list[int]
