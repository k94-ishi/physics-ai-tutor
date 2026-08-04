from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from physics_ai_tutor.database.dependency import get_db

router = APIRouter()


@router.get("/health")
def helath_check():
    return {"status": "ok"}


@router.get("/db-health")
def db_health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }
