from datetime import datetime

from pydantic import BaseModel, Field


class ConceptResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class ConceptExtractionRequest(BaseModel):
    question_ids: list[int] = Field(min_length=1, max_length=100)


class ConceptExtractionResult(BaseModel):
    question_id: int
    success: bool
    concepts: list[str] = Field(default_factory=list)


class ConceptExtractionBatchResponse(BaseModel):
    results: list[ConceptExtractionResult]
