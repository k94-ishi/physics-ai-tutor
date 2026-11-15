import logging
from datetime import UTC, date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import require_admin
from physics_ai_tutor.database.dependency import get_async_db, get_db
from physics_ai_tutor.schemas.admin_stats import (
    AdminStatsResponse,
    ReviewAgreementResponse,
)
from physics_ai_tutor.schemas.ai_review_run import (
    AiReviewRunResponse,
    PendingCountResponse,
    StartRunRequest,
)
from physics_ai_tutor.schemas.token import JWTPayload
from physics_ai_tutor.services import (
    ai_review_service,
    review_export_service,
    review_metrics_service,
    stats_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    dependencies=[Depends(require_admin)],
)
async def get_usage_stats(
    days: int = Query(default=14, ge=1, le=90),
    db: AsyncSession = Depends(get_async_db),
):
    return await stats_service.fetch_usage_stats(db, days)


@router.get("/reviews/export", dependencies=[Depends(require_admin)])
async def export_reviews(
    since: date | None = Query(default=None),
    all: bool = Query(default=False),
    db: AsyncSession = Depends(get_async_db),
):
    """The review dataset as JSONL, for when the CLI has no DB access.

    Defaults to the 2026-10-28 data cutoff; `all=true` returns everything.
    The dataset is small enough to build in memory.
    """
    if all:
        start: datetime | None = None
    elif since is None:
        start = review_export_service.default_since()
    else:
        start = datetime.combine(since, datetime.min.time(), tzinfo=UTC)

    rows = [row async for row in review_export_service.iter_export_rows(db, start)]
    body = "".join(review_export_service.to_jsonl(rows))

    return Response(
        content=body,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="reviews.jsonl"'},
    )


@router.get(
    "/stats/review-agreement",
    response_model=ReviewAgreementResponse,
    dependencies=[Depends(require_admin)],
)
async def get_review_agreement(
    since: date | None = Query(default=None),
    db: AsyncSession = Depends(get_async_db),
):
    """How often the AI pre-reviewer agreed with the teacher who came after."""
    start = (
        datetime.combine(since, datetime.min.time(), tzinfo=UTC)
        if since is not None
        else review_export_service.default_since()
    )

    return await review_metrics_service.build_report(db, start)


@router.post("/ai-review/runs", response_model=AiReviewRunResponse, status_code=202)
def start_ai_review_run(
    data: StartRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    try:
        run = ai_review_service.start_run(
            db,
            scope=data.scope.value,
            trigger="manual",
            question_ids=data.question_ids,
            limit=data.limit,
            started_by=int(current_user.sub),
        )
    except ai_review_service.RunInProgressError:
        raise HTTPException(
            status_code=409,
            detail="An AI review run is already in progress",
        ) from None
    except ai_review_service.DailyCapExhaustedError:
        raise HTTPException(
            status_code=429,
            detail="The daily AI review budget is exhausted",
        ) from None

    logger.info(
        "Admin action: user_id=%s action=start_ai_review_run run_id=%d "
        "scope=%s requested=%d",
        current_user.sub,
        run.id,
        run.scope,
        run.requested_count,
    )
    # Async so the run grades a few questions at a time ([72]).
    background_tasks.add_task(ai_review_service.async_execute_run_in_background, run.id)

    return run


@router.get(
    "/ai-review/runs",
    response_model=list[AiReviewRunResponse],
    dependencies=[Depends(require_admin)],
)
def list_ai_review_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ai_review_service.list_runs(db, limit)


@router.get(
    "/ai-review/runs/{run_id}",
    response_model=AiReviewRunResponse,
    dependencies=[Depends(require_admin)],
)
def get_ai_review_run(
    run_id: int,
    db: Session = Depends(get_db),
):
    run = ai_review_service.get_run(db, run_id)

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return run


@router.get(
    "/ai-review/pending-count",
    response_model=PendingCountResponse,
    dependencies=[Depends(require_admin)],
)
def get_ai_review_pending_count(
    db: Session = Depends(get_db),
):
    """How many questions await review, and how many a run could do now.

    `pending` and `stale` are true totals; a run is additionally bounded by
    `remaining`, so `would_review_*` is what a confirm dialog should quote.
    """
    from physics_ai_tutor.core.config import settings

    remaining = ai_review_service.remaining_daily_budget(db)
    pending = ai_review_service.count_pending(db)
    stale = ai_review_service.count_stale(db)

    return PendingCountResponse(
        pending=pending,
        stale=stale,
        daily_cap=settings.ai_review_daily_cap,
        used_24h=settings.ai_review_daily_cap - remaining,
        remaining=remaining,
        would_review_pending=min(pending, remaining),
        would_review_stale=min(stale, remaining),
    )
