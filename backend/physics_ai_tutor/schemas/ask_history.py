from datetime import datetime

from pydantic import BaseModel

from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import QuestionStatus


class MyQuestionEntry(BaseModel):
    """One ask in the student's history, with the current state of the row.

    `answer` is withheld for rejected questions; the UI shows a neutral
    "withdrawn by a teacher" message instead of the rejected text.
    """

    question_id: int
    question: str
    answer: str | None
    language: Language
    provenance: str | None
    status: QuestionStatus
    asked_at: datetime


class MyQuestionsResponse(BaseModel):
    items: list[MyQuestionEntry]
    total: int
    page: int
    size: int
