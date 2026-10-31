import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from physics_ai_tutor.api.dependencies import (
    ACCESS_TOKEN_COOKIE_NAME,
    get_current_db_user,
    get_current_user,
    require_admin,
)
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.models.user import User
from physics_ai_tutor.repositories import user_repository
from physics_ai_tutor.schemas.ask_history import MyQuestionsResponse
from physics_ai_tutor.schemas.auth import CurrentUser
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.token import JWTPayload
from physics_ai_tutor.schemas.user import (
    PasswordChangeRequest,
    UserCreate,
    UserResponse,
)
from physics_ai_tutor.services import ask_history_service, user_service

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


@router.get("/me/questions", response_model=MyQuestionsResponse)
def get_my_questions(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    lang: Language = Query(default=Language.JA),
    payload: JWTPayload = Depends(get_current_user),
    db=Depends(get_db),
):
    """The caller's ask history with each question's current state.

    Unreviewed answers here are ones this user already saw when asking
    (the cache serves them to the identical question), so returning them
    does not widen the public visibility rule.
    """
    return ask_history_service.fetch_my_questions(
        db, int(payload.sub), page, size, lang
    )


@router.get("/me/profile", response_model=UserResponse)
def get_my_profile(
    user: User = Depends(get_current_db_user),
):
    return user


@router.delete("/me", status_code=204)
def delete_my_account(
    user: User = Depends(get_current_db_user),
    db=Depends(get_db),
):
    """Self-service account deletion for students.

    Admins are refused so an admin cannot remove the last admin by
    accident; they use the admin flow, which blocks self-deletion too.
    Review history survives with `reviewer_id` set to NULL.
    """
    if user.role == "admin":
        raise HTTPException(
            status_code=400,
            detail="Admins cannot delete their own account",
        )

    user_id = user.id
    user_service.delete_user(db, user)
    logger.info("Account self-deleted: user_id=%s", user_id)

    response = Response(status_code=204)
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE_NAME, path="/")

    return response


@router.get("", response_model=list[UserResponse])
def list_users(
    db=Depends(get_db),
    _: JWTPayload = Depends(require_admin),
):
    return user_service.list_users(db)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    data: UserCreate,
    db=Depends(get_db),
    current_user: JWTPayload = Depends(require_admin),
):
    if user_repository.get_user_by_email(db, data.email) is not None:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    user = user_service.create_user(db, data.email, data.password, role=data.role)
    logger.info(
        "Admin action: user_id=%s action=create_user target_email=%s target_role=%s",
        current_user.sub,
        user.email,
        user.role,
    )

    return user


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
