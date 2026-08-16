from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints


class AskAiRequest(BaseModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    mode: Literal["RAG"] | None = None


class AskAiResponse(BaseModel):
    answer: str
