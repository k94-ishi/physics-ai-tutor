from pydantic import BaseModel


class QuestionCreate(BaseModel):
    question: str
    answer: str


class QuestionUpdate(QuestionCreate):
    pass


class QuestionBulkCreate(BaseModel):
    questions: list[QuestionCreate]

class QuestionResponse(BaseModel):
    id: int
    question: str
    answer: str

    model_config = {
        "from_attributes": True
    }