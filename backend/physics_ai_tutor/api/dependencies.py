import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import jwt
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import APIKeyCookie
from pydantic import ValidationError
from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import RateLimitExceeded
from physics_ai_tutor.core.jwt import create_access_token, decode_access_token
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.models.user import User
from physics_ai_tutor.repositories import user_repository
from physics_ai_tutor.schemas.token import JWTPayload, UserRole
from physics_ai_tutor.services import rate_limit_service

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
        samesite=settings.same_site,
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


def get_current_user_optional(
    token: str | None = Depends(cookie_scheme),
) -> JWTPayload | None:
    """Best-effort auth check for read-only visibility filtering only.

    Unlike `get_current_user`, this never raises 401 and never performs the
    sliding-refresh side effect (no DB lookup, no `Set-Cookie`) - it exists
    purely so public endpoints can distinguish an admin caller from anyone
    else without requiring authentication. Never use this to gate a
    mutating endpoint; use `require_admin` for that.
    """
    if token is None:
        return None

    try:
        return decode_access_token(token)
    except (jwt.PyJWTError, ValidationError):
        return None


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


def get_client_ip(request: Request) -> str:
    """Resolve the caller's IP for rate limiting.

    The rightmost entry in X-Forwarded-For is the one appended by our own
    trusted proxy (Render/Vercel), not the client - the client can prepend
    arbitrary fake entries to the left, so taking the leftmost value would
    let them spoof a fresh IP on every request and bypass the limiter.
    """
    if settings.trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[-1].strip()

    return request.client.host if request.client else "unknown"


AI_ASK_ACTION = "ai_ask"
LOGIN_ACTION = "login"

ANONYMOUS_AI_ASK_LIMITS = [(3, 3600), (10, 86400)]
USER_AI_ASK_LIMITS = [(10, 3600), (30, 86400)]
ADMIN_AI_ASK_LIMITS = [(3000, 86400)]
LOGIN_LIMITS = [(5, 60), (20, 3600)]


@dataclass
class AiAskRateLimit:
    """Deferred rate-limit hit for one ask request.

    The dependency only checks the limit; the route records the hit via
    this handle when the request actually triggers a generation, so cache
    hits stay free.
    """

    bucket_key: str

    def record(self, db: Session) -> None:
        rate_limit_service.record(db, AI_ASK_ACTION, self.bucket_key)


def enforce_ai_ask_rate_limit(
    request: Request,
    user: JWTPayload | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> AiAskRateLimit:
    """Signed-in callers are limited per account; anonymous callers per IP."""
    if user is None:
        bucket_key = f"ip:{get_client_ip(request)}"
        limits = ANONYMOUS_AI_ASK_LIMITS
    elif user.role == UserRole.ADMIN:
        bucket_key = f"user:{user.sub}"
        limits = ADMIN_AI_ASK_LIMITS
    else:
        bucket_key = f"user:{user.sub}"
        limits = USER_AI_ASK_LIMITS

    try:
        rate_limit_service.check(db, AI_ASK_ACTION, bucket_key, limits)
    except RateLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
        ) from None

    return AiAskRateLimit(bucket_key=bucket_key)


def enforce_login_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    bucket_key = f"ip:{get_client_ip(request)}"

    try:
        rate_limit_service.check(db, LOGIN_ACTION, bucket_key, LOGIN_LIMITS)
    except RateLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later.",
        ) from None

    # Every login attempt counts, successful or not.
    rate_limit_service.record(db, LOGIN_ACTION, bucket_key)
