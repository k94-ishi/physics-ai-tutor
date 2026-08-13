from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import (
    ACCESS_TOKEN_COOKIE_NAME,
    set_access_token_cookie,
)
from physics_ai_tutor.core.jwt import create_access_token
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.auth import CurrentUser, LoginRequest
from physics_ai_tutor.services.auth_service import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=CurrentUser)
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, data.email, data.password)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
    )
    set_access_token_cookie(response, access_token)

    return CurrentUser(id=user.id, role=user.role)


@router.post("/logout", status_code=204)
def logout(response: Response):
    """Clear the access token cookie.

    There is no server-side token blacklist, so a raw JWT captured before
    logout remains technically valid until it naturally expires (at most
    `jwt_access_token_expire_minutes`). This endpoint only clears the
    cookie so the browser stops sending it; it does not require an
    already-valid session, so an expired/garbage cookie can still be
    cleared successfully.
    """
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.status_code = 204
    return response
