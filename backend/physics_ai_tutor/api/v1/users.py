import logging

from fastapi import APIRouter, Depends, HTTPException, Response

from physics_ai_tutor.api.dependencies import (
    get_current_db_user,
    get_current_user,
    require_admin,
)
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.models.user import User
from physics_ai_tutor.schemas.auth import CurrentUser
from physics_ai_tutor.schemas.token import JWTPayload
from physics_ai_tutor.schemas.user import PasswordChangeRequest, UserResponse
from physics_ai_tutor.services import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=CurrentUser)
def get_me(
    payload: JWTPayload = Depends(get_current_user),
):
    return CurrentUser(id=int(payload.sub), role=payload.role)


@router.put("/me/password", status_code=204)
def change_my_password(
    data: PasswordChangeRequest,
    user: User = Depends(get_current_db_user),
    db=Depends(get_db),
):
    changed = user_service.change_password(
        db, user, data.current_password, data.new_password
    )

    if not changed:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )

    return Response(status_code=204)


@router.get("", response_model=list[UserResponse])
def list_users(
    db=Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    return user_service.list_users(db)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db=Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    user = user_service.get_user(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db=Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    if str(user_id) == current_user.sub:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account",
        )

    user = user_service.get_user(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    user_service.delete_user(db, user)
    logger.info(
        "Admin action: user_id=%s action=delete_user target_user_id=%s",
        current_user.sub,
        user_id,
    )

    return Response(status_code=204)
