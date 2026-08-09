from pydantic import BaseModel


class SimilarQuestionRequest(BaseModel):
    query: str
    limit: int = 5


class SimilarQuestionResponse(BaseModel):
    id: int
    question: str
    answer: str
    distance: float
