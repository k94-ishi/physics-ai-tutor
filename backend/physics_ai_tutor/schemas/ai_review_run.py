from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RunScope(StrEnum):
    PENDING = "pending"
    STALE = "stale"
    SELECTED = "selected"


class StartRunRequest(BaseModel):
    scope: RunScope
    question_ids: list[int] | None = Field(default=None, max_length=200)
    limit: int | None = Field(default=None, ge=1, le=200)


class AiReviewRunResponse(BaseModel):
    id: int
    trigger: str
    scope: RunScope
    started_by_user_id: int | None
    requested_count: int
    reviewed_count: int
    failed_count: int
    prompt_tokens: int
    completion_tokens: int
    status: str
    error: str | None
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class PendingCountResponse(BaseModel):
    pending: int
    stale: int
    daily_cap: int
    used_24h: int
    remaining: int
