import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from physics_ai_tutor.api.dependencies import (
    ACCESS_TOKEN_COOKIE_NAME,
    enforce_login_rate_limit,
    set_access_token_cookie,
)
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import (
    GoogleAccountConflictError,
    GoogleAuthError,
)
from physics_ai_tutor.core.jwt import create_access_token
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.schemas.auth import AuthProviders, CurrentUser, LoginRequest
from physics_ai_tutor.services import google_auth_service
from physics_ai_tutor.services.auth_service import authenticate_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_STATE_COOKIE_NAME = "google_oauth_state"
GOOGLE_STATE_COOKIE_PATH = "/api/v1/auth/google"
GOOGLE_STATE_MAX_AGE_SECONDS = 600


@router.get("/providers", response_model=AuthProviders)
def get_providers():
    return AuthProviders(password=True, google=google_auth_service.is_enabled())


@router.post(
    "/login",
    response_model=CurrentUser,
    dependencies=[Depends(enforce_login_rate_limit)],
)
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


def _require_google_enabled() -> None:
    if not google_auth_service.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Google Sign-In is not configured",
        )


def _login_page_redirect(error: str) -> RedirectResponse:
    response = RedirectResponse(
        url=f"{settings.frontend_url}/login?error={error}", status_code=302
    )
    response.delete_cookie(key=GOOGLE_STATE_COOKIE_NAME, path=GOOGLE_STATE_COOKIE_PATH)

    return response


@router.get("/google/login", status_code=302)
def google_login(_: None = Depends(_require_google_enabled)):
    """Send the browser to Google with a fresh anti-CSRF state."""
    state = google_auth_service.generate_state()

    response = RedirectResponse(
        url=google_auth_service.build_authorization_url(state), status_code=302
    )
    # SameSite=lax so the cookie is sent on the top-level redirect back.
    response.set_cookie(
        key=GOOGLE_STATE_COOKIE_NAME,
        value=state,
        max_age=GOOGLE_STATE_MAX_AGE_SECONDS,
        path=GOOGLE_STATE_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )

    return response


@router.get("/google/callback", status_code=302)
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(_require_google_enabled),
):
    """Finish the Google flow and issue the same session cookie as /login."""
    if error is not None or code is None or state is None:
        logger.info("Google login aborted: error=%s", error)
        return _login_page_redirect("google_failed")

    expected_state = request.cookies.get(GOOGLE_STATE_COOKIE_NAME)

    if expected_state is None or not secrets.compare_digest(expected_state, state):
        logger.warning("Google login rejected: reason=state_mismatch")
        return _login_page_redirect("google_failed")

    try:
        identity = google_auth_service.exchange_code(code)
        user = google_auth_service.login_or_register(db, identity)
    except GoogleAuthError:
        return _login_page_redirect("google_failed")
    except GoogleAccountConflictError:
        return _login_page_redirect("account_exists")

    response = RedirectResponse(url=f"{settings.frontend_url}/", status_code=302)
    response.delete_cookie(key=GOOGLE_STATE_COOKIE_NAME, path=GOOGLE_STATE_COOKIE_PATH)
    set_access_token_cookie(
        response, create_access_token(subject=str(user.id), role=user.role)
    )

    return response
