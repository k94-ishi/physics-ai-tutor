import json
import logging
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

import jwt
from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import (
    GoogleAccountConflictError,
    GoogleAuthError,
)
from physics_ai_tutor.models.user import User
from physics_ai_tutor.repositories import user_repository

logger = logging.getLogger(__name__)

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")

# Only what is needed to identify the student; no profile or avatar.
GOOGLE_SCOPES = "openid email"

TOKEN_REQUEST_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str


def is_enabled() -> bool:
    return bool(
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_redirect_uri
    )


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def build_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "state": state,
        # Let students pick a personal account over a blocked school one.
        "prompt": "select_account",
    }

    return f"{GOOGLE_AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(code: str) -> GoogleIdentity:
    """Trade the authorization code for an ID token and read the identity."""
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode()
    request = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request, timeout=TOKEN_REQUEST_TIMEOUT_SECONDS
        ) as response:
            payload = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("Google token exchange failed: %s", exc)
        raise GoogleAuthError("token exchange failed") from exc

    id_token = payload.get("id_token")

    if not isinstance(id_token, str):
        raise GoogleAuthError("token response has no id_token")

    return parse_id_token(id_token)


def parse_id_token(id_token: str) -> GoogleIdentity:
    """Validate the ID token claims and extract the identity.

    The token arrives straight from Google's token endpoint over TLS, which
    OpenID Connect allows in place of checking the signature, so only the
    claims are verified here.
    """
    try:
        claims = jwt.decode(id_token, options={"verify_signature": False})
    except jwt.PyJWTError as exc:
        raise GoogleAuthError("id_token is not a valid JWT") from exc

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise GoogleAuthError("unexpected issuer")

    if claims.get("aud") != settings.google_client_id:
        raise GoogleAuthError("unexpected audience")

    expires_at = claims.get("exp")

    if not isinstance(expires_at, int | float) or expires_at <= time.time():
        raise GoogleAuthError("id_token expired")

    sub = claims.get("sub")
    email = claims.get("email")

    if not isinstance(sub, str) or not isinstance(email, str):
        raise GoogleAuthError("id_token lacks sub or email")

    if claims.get("email_verified") is not True:
        raise GoogleAuthError("e-mail not verified by Google")

    return GoogleIdentity(sub=sub, email=email.lower())


def login_or_register(db: Session, identity: GoogleIdentity) -> User:
    """Return the Google account for this identity, creating it on first use.

    Never links to an existing password account by e-mail; that is rejected.
    """
    user = user_repository.get_user_by_google_sub(db, identity.sub)

    if user is not None:
        logger.info("Google login success: user_id=%s role=%s", user.id, user.role)
        return user

    if user_repository.get_user_by_email(db, identity.email) is not None:
        logger.warning("Google login rejected: reason=email_owned_by_password_account")
        raise GoogleAccountConflictError(identity.email)

    user = User(
        email=identity.email,
        auth_provider="google",
        google_sub=identity.sub,
        role="user",
    )

    try:
        user_repository.create_user(db, user)
        db.commit()
        db.refresh(user)
    except Exception:
        logger.warning("Rolling back transaction: operation=google_register")
        db.rollback()
        raise

    logger.info("Google account created: user_id=%s", user.id)

    return user
