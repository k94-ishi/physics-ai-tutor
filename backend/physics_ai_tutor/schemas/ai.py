from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints


class AskAiRequest(BaseModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=200)
    ]
    mode: Literal["RAG"] | None = None
    retrieved_question_ids: list[int] | None = None


class AskAiResponse(BaseModel):
    answer: str
