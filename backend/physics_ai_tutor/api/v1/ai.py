import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.api.dependencies import (
    AiAskRateLimit,
    enforce_ai_ask_rate_limit,
    get_current_user_optional,
)
from physics_ai_tutor.database.dependency import get_async_db
from physics_ai_tutor.schemas.ai import AskAiRequest, AskAiResponse
from physics_ai_tutor.schemas.token import JWTPayload
from physics_ai_tutor.services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ask", response_model=AskAiResponse)
async def ask_ai(
    request: AskAiRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    rate_limit: AiAskRateLimit = Depends(enforce_ai_ask_rate_limit),
    user: JWTPayload | None = Depends(get_current_user_optional),
):
    outcome = await ai_service.ask(
        db,
        request,
        user_id=int(user.sub) if user is not None else None,
        record_generation=lambda: rate_limit.record(db),
        rate_limit_bucket=rate_limit.bucket_key,
    )
    if outcome.saved_question_id is not None:
        background_tasks.add_task(
            ai_service.post_generation_tasks, outcome.saved_question_id
        )
    return outcome.response
