from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import require_admin
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.admin_stats import AdminStatsResponse
from physics_ai_tutor.services import review_export_service, stats_service

router = APIRouter(prefix="/admin", tags=["admin"])


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
