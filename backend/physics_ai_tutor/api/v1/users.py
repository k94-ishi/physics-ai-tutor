from fastapi import APIRouter, Depends

from physics_ai_tutor.api.dependencies import get_current_db_user
from physics_ai_tutor.models.user import User
from physics_ai_tutor.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(
    user: User = Depends(get_current_db_user),
):
    return user
