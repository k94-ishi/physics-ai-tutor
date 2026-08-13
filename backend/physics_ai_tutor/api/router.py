from fastapi import APIRouter

from physics_ai_tutor.api.v1 import ai, auth, health, questions, users

router = APIRouter()

router.include_router(health.router, prefix="/api/v1")
router.include_router(questions.router, prefix="/api/v1")
router.include_router(auth.router, prefix="/api/v1")
router.include_router(users.router, prefix="/api/v1")
router.include_router(ai.router, prefix="/api/v1")
