import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from physics_ai_tutor.api import sse
from physics_ai_tutor.api.dependencies import (
    AiAskRateLimit,
    enforce_ai_ask_rate_limit,
    get_current_user_optional,
)
from physics_ai_tutor.core.exceptions import DeepSeekGenerationError
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


@router.post("/ask/stream")
async def ask_ai_stream(
    request: AskAiRequest,
    db: AsyncSession = Depends(get_async_db),
    rate_limit: AiAskRateLimit = Depends(enforce_ai_ask_rate_limit),
    user: JWTPayload | None = Depends(get_current_user_optional),
):
    """`/ask` as a stream, so the student reads while it generates ([71]).

    Same request body, auth, rate limit and cache tiers; the answer
    arrives as `delta` events and the metadata `/ask` returns in its body
    comes last, as `done`.
    """
    # The generator fills this once the row is written, which is after
    # the handler has returned; the background task reads it then.
    saved: dict[str, int | None] = {"question_id": None}

    async def events() -> AsyncIterator[str]:
        try:
            async for item in ai_service.ask_stream(
                db,
                request,
                user_id=int(user.sub) if user is not None else None,
                record_generation=lambda: rate_limit.record(db),
                rate_limit_bucket=rate_limit.bucket_key,
                saved=saved,
            ):
                if item.kind == "delta":
                    yield sse.event("delta", {"text": item.text})
                elif item.kind == "done":
                    assert item.response is not None
                    yield sse.event("done", item.response.model_dump(mode="json"))
                else:
                    yield sse.event("error", {"detail": item.detail})
        except DeepSeekGenerationError:
            # The status line is already 200 by now, so the failure has to
            # travel as an event rather than a 503.
            logger.error("Streamed ask failed", exc_info=True)
            yield sse.event(
                "error",
                {"detail": "DeepSeek generation failed. Please try again later."},
            )

    async def post_generation() -> None:
        question_id = saved["question_id"]
        if question_id is not None:
            await ai_service.post_generation_tasks(question_id)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Render and other nginx-style proxies buffer by default,
            # which would defeat the point of streaming.
            "X-Accel-Buffering": "no",
        },
        background=BackgroundTask(post_generation),
    )
