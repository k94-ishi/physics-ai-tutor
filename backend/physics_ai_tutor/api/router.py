from fastapi import APIRouter

from physics_ai_tutor.api.v1 import (
    admin,
    admin_questions,
    ai,
    auth,
    concepts,
    health,
    questions,
    users,
)

router = APIRouter()

router.include_router(health.router, prefix="/api/v1")
router.include_router(questions.router, prefix="/api/v1")
# Admin question routes share the prefix; registered after the public ones.
router.include_router(admin_questions.router, prefix="/api/v1")
router.include_router(auth.router, prefix="/api/v1")
router.include_router(users.router, prefix="/api/v1")
router.include_router(ai.router, prefix="/api/v1")
router.include_router(admin.router, prefix="/api/v1")
router.include_router(concepts.router, prefix="/api/v1")
router.include_router(concepts.admin_router, prefix="/api/v1")
