import logging
from datetime import UTC, date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import require_admin
from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.models import AiReviewRun
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


def execute_run_in_background(run_id: int) -> None:
    """Run the reviewer after the response is sent, on its own session."""
    db = SessionLocal()
    try:
        ai_review_service.execute_run(db, run_id)
    except Exception:
        logger.exception("Background AI review run crashed: run_id=%d", run_id)
    finally:
        db.close()


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    dependencies=[Depends(require_admin)],
)
def get_usage_stats(
    days: int = Query(default=14, ge=1, le=90),
    db: Session = Depends(get_db),
):
    return stats_service.fetch_usage_stats(db, days)


@router.get("/reviews/export", dependencies=[Depends(require_admin)])
def export_reviews(
    since: date | None = Query(default=None),
    all: bool = Query(default=False),
    db: Session = Depends(get_db),
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

    body = "".join(
        review_export_service.to_jsonl(
            review_export_service.iter_export_rows(db, start)
        )
    )

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
def get_review_agreement(
    since: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """How often the AI pre-reviewer agreed with the teacher who came after."""
    start = (
        datetime.combine(since, datetime.min.time(), tzinfo=UTC)
        if since is not None
        else review_export_service.default_since()
    )

    return review_metrics_service.build_report(db, start)


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
    background_tasks.add_task(execute_run_in_background, run.id)

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
    return db.query(AiReviewRun).order_by(AiReviewRun.id.desc()).limit(limit).all()


@router.get(
    "/ai-review/runs/{run_id}",
    response_model=AiReviewRunResponse,
    dependencies=[Depends(require_admin)],
)
def get_ai_review_run(
    run_id: int,
    db: Session = Depends(get_db),
):
    run = db.get(AiReviewRun, run_id)

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
    """How many questions a run would touch, and the remaining budget."""
    from physics_ai_tutor.core.config import settings

    remaining = ai_review_service.remaining_daily_budget(db)

    return PendingCountResponse(
        pending=len(ai_review_service.eligible_question_ids(db, "pending")),
        stale=len(ai_review_service.eligible_question_ids(db, "stale")),
        daily_cap=settings.ai_review_daily_cap,
        used_24h=settings.ai_review_daily_cap - remaining,
        remaining=remaining,
    )
