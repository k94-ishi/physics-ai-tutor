from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.services import health_service

router = APIRouter(tags=["health"])


@router.get("/health")
def helath_check():
    return {"status": "ok"}


@router.get("/db-health")
def db_health_check(db: Session = Depends(get_db)):
    health_service.check_database(db)

    return {
        "status": "ok",
        "database": "connected",
    }
