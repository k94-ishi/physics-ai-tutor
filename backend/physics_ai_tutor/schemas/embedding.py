from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class SimilarQuestionRequest(BaseModel):
    query: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    limit: int = Field(default=5, ge=1, le=50)


class SimilarQuestionResponse(BaseModel):
    id: int
    question: str
    answer: str
    distance: float
