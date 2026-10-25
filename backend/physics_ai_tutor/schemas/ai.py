from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import QuestionStatus


class AskAiRequest(BaseModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=200)
    ]
    mode: Literal["RAG"] | None = None
    retrieved_question_ids: list[int] | None = None
    language: Language = Language.JA


class AskAiResponse(BaseModel):
    answer: str
    language: Language
    # True when the answer came from an existing row instead of DeepSeek.
    cached: bool = False
    question_id: int | None = None
    status: QuestionStatus | None = None
