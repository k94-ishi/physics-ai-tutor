from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.database.dependency import get_async_db
from physics_ai_tutor.services import health_service

router = APIRouter(tags=["health"])


# The operationId typo is public API; renaming it is deferred ([57]).
@router.get("/health")
async def helath_check():
    return {"status": "ok"}


@router.get("/db-health")
async def db_health_check(db: AsyncSession = Depends(get_async_db)):
    await health_service.check_database(db)

    return {
        "status": "ok",
        "database": "connected",
    }
