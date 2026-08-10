from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

QuestionText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]
AnswerText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]


class QuestionCreate(BaseModel):
    question: QuestionText
    answer: AnswerText


class QuestionUpdate(QuestionCreate):
    pass


class QuestionBulkCreate(BaseModel):
    questions: list[QuestionCreate] = Field(min_length=1, max_length=50)


class QuestionResponse(BaseModel):
    id: int
    question: str
    answer: str

    model_config = {
        "from_attributes": True
    }


class QuestionListResponse(BaseModel):
    items: list[QuestionResponse]
    total: int
    page: int
    size: int
