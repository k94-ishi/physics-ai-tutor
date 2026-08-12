import logging
from datetime import UTC, datetime

import jwt
from fastapi import Depends, HTTPException, Response
from fastapi.security import APIKeyCookie
from pydantic import ValidationError
from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.jwt import create_access_token, decode_access_token
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.models.user import User
from physics_ai_tutor.repositories import user_repository
from physics_ai_tutor.schemas.token import JWTPayload, UserRole

logger = logging.getLogger(__name__)

ACCESS_TOKEN_COOKIE_NAME = "access_token"

cookie_scheme = APIKeyCookie(name=ACCESS_TOKEN_COOKIE_NAME, auto_error=False)


def set_access_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def get_current_user(
    response: Response,
    db: Session = Depends(get_db),
    token: str | None = Depends(cookie_scheme),
) -> JWTPayload:
    """Validate the access token cookie and refresh it if expiration is near.

    Side effects: when the token's remaining lifetime is at or below
    `settings.jwt_refresh_threshold_minutes`, this
    1) looks up the user in the DB to sync the role claim, rejecting the
       request with 401 if the user no longer exists, and
    2) reissues a new token (synced role, same sub/jti) and calls
       `response.set_cookie(...)`, which adds a `Set-Cookie` header to the
       outgoing response.

    Outside of a refresh, this never touches the DB, so a role change or
    account deletion only takes effect the next time the session's token
    enters the refresh window (roughly every `jwt_access_token_expire_minutes
    - jwt_refresh_threshold_minutes` for a continuously active session), or
    at the next login for an idle/expired session. There is still no
    server-side blacklist, so this is a bounded delay, not immediate
    revocation.
    """
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    try:
        payload = decode_access_token(token)
    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        ) from None

    now_ts = int(datetime.now(UTC).timestamp())
    remaining_seconds = payload.exp - now_ts
    refresh_threshold_seconds = settings.jwt_refresh_threshold_minutes * 60

    if remaining_seconds <= refresh_threshold_seconds:
        user = user_repository.get_user_by_id(db, int(payload.sub))

        if user is None:
            logger.warning(
                "Session rejected: user_id=%s reason=user_deleted", payload.sub
            )
            raise HTTPException(
                status_code=401,
                detail="User no longer exists",
            )

        if user.role != payload.role:
            logger.info(
                "Role synced on refresh: user_id=%s old_role=%s new_role=%s",
                payload.sub,
                payload.role,
                user.role,
            )
            payload = payload.model_copy(update={"role": user.role})

        new_token = create_access_token(
            subject=payload.sub,
            role=payload.role,
            jti=payload.jti,
        )
        set_access_token_cookie(response, new_token)

    return payload


def get_current_db_user(
    payload: JWTPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user = user_repository.get_user_by_id(db, int(payload.sub))

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User no longer exists",
        )

    return user


def require_admin(
    user: JWTPayload = Depends(get_current_user),
) -> JWTPayload:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin permission required",
        )

    return user
