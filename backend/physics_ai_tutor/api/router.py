from fastapi import APIRouter

from physics_ai_tutor.api.v1 import health

router = APIRouter()

router.include_router(
    health.router,
    prefix="/api/v1",
)
