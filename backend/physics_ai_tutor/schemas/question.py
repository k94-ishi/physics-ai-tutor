from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, StringConstraints

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


class QuestionCreate(BaseModel):
    question: QuestionText
    answer: AnswerText


class QuestionUpdate(QuestionCreate):
    pass


class QuestionResponse(BaseModel):
    id: int
    question: str
    answer: str
    status: QuestionStatus
    source: QuestionSource

    model_config = {
        "from_attributes": True
    }


class QuestionListResponse(BaseModel):
    items: list[QuestionResponse]
    total: int
    page: int
    size: int


class QuestionImportResponse(BaseModel):
    created_count: int
    questions: list[QuestionResponse]
