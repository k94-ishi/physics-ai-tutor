from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import require_admin
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.admin_stats import AdminStatsResponse
from physics_ai_tutor.services import stats_service

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
