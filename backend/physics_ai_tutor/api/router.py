from fastapi import APIRouter

from physics_ai_tutor.api.v1 import health
from physics_ai_tutor.api.v1 import questions


router = APIRouter()

router.include_router(
    health.router,
    prefix="/api/v1",
)

router.include_router(
    questions.router,
    prefix="/api/v1",
)