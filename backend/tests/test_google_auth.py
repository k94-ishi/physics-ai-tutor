import time
from urllib.parse import parse_qs, urlparse

import jwt as pyjwt
import pytest

from physics_ai_tutor.api.dependencies import ACCESS_TOKEN_COOKIE_NAME
from physics_ai_tutor.api.v1.auth import GOOGLE_STATE_COOKIE_NAME
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import GoogleAuthError
from physics_ai_tutor.models import User
from physics_ai_tutor.services import google_auth_service
from physics_ai_tutor.services.google_auth_service import GoogleIdentity
from physics_ai_tutor.services.user_service import create_user

PROVIDERS_PATH = "/api/v1/auth/providers"
GOOGLE_LOGIN_PATH = "/api/v1/auth/google/login"
GOOGLE_CALLBACK_PATH = "/api/v1/auth/google/callback"
LOGIN_PATH = "/api/v1/auth/login"
ME_PATH = "/api/v1/users/me"
PASSWORD_PATH = "/api/v1/users/me/password"
USERS_PATH = "/api/v1/users"

CLIENT_ID = "test-client-id.apps.googleusercontent.com"
FRONTEND_URL = "http://frontend.test"
STATE = "test-state-value"
IDENTITY = GoogleIdentity(sub="google-sub-123", email="student@gmail.com")


@pytest.fixture
def google_disabled(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", None)


@pytest.fixture
def google_enabled(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", CLIENT_ID)
    monkeypatch.setattr(settings, "google_client_secret", "test-secret")
    monkeypatch.setattr(
        settings, "google_redirect_uri", f"http://api.test{GOOGLE_CALLBACK_PATH}"
    )
    monkeypatch.setattr(settings, "frontend_url", FRONTEND_URL)


@pytest.fixture
def exchange_returns(monkeypatch):
    def _set(identity):
        monkeypatch.setattr(google_auth_service, "exchange_code", lambda code: identity)

    return _set


def _callback(client, *, state=STATE, cookie_state=STATE, **params):
    if cookie_state is not None:
        client.cookies.set(GOOGLE_STATE_COOKIE_NAME, cookie_state)

    query = {"code": "auth-code", "state": state, **params}

    return client.get(GOOGLE_CALLBACK_PATH, params=query, follow_redirects=False)


def _id_token(**overrides) -> str:
    claims = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "exp": int(time.time()) + 300,
        "sub": IDENTITY.sub,
        "email": "Student@gmail.com",
        "email_verified": True,
        **overrides,
    }
    # The signature is not checked, so any key will do.
    return pyjwt.encode(claims, "x" * 32, algorithm="HS256")


def test_providers_reports_google_disabled_without_config(client, google_disabled):
    response = client.get(PROVIDERS_PATH)

    assert response.status_code == 200
    assert response.json() == {"password": True, "google": False}


def test_providers_reports_google_enabled_with_config(client, google_enabled):
    response = client.get(PROVIDERS_PATH)

    assert response.json() == {"password": True, "google": True}


def test_google_login_unavailable_without_config(client, google_disabled):
    response = client.get(GOOGLE_LOGIN_PATH, follow_redirects=False)

    assert response.status_code == 503


def test_google_login_redirects_to_google_with_state_cookie(client, google_enabled):
    response = client.get(GOOGLE_LOGIN_PATH, follow_redirects=False)

    assert response.status_code == 302

    location = urlparse(response.headers["location"])
    query = parse_qs(location.query)

    assert location.netloc == "accounts.google.com"
    assert query["client_id"] == [CLIENT_ID]
    assert query["scope"] == ["openid email"]
    assert query["response_type"] == ["code"]
    assert query["state"] == [client.cookies.get(GOOGLE_STATE_COOKIE_NAME)]

    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


def test_callback_creates_google_account_and_logs_in(
    client, db, google_enabled, exchange_returns
):
    exchange_returns(IDENTITY)

    response = _callback(client)

    assert response.status_code == 302
    assert response.headers["location"] == f"{FRONTEND_URL}/"
    assert client.cookies.get(ACCESS_TOKEN_COOKIE_NAME) is not None

    user = db.query(User).filter_by(email=IDENTITY.email).one()
    assert user.auth_provider == "google"
    assert user.google_sub == IDENTITY.sub
    assert user.hashed_password is None
    assert user.role == "user"

    me = client.get(ME_PATH)
    assert me.status_code == 200
    assert me.json() == {"id": user.id, "role": "user"}


def test_callback_reuses_existing_google_account(
    client, db, google_enabled, exchange_returns
):
    exchange_returns(IDENTITY)

    _callback(client)
    first_id = db.query(User).filter_by(google_sub=IDENTITY.sub).one().id

    _callback(client)

    users = db.query(User).filter_by(google_sub=IDENTITY.sub).all()
    assert [user.id for user in users] == [first_id]


def test_callback_rejects_email_owned_by_password_account(
    client, db, google_enabled, exchange_returns
):
    create_user(db, IDENTITY.email, "password123", role="user")
    exchange_returns(IDENTITY)

    response = _callback(client)

    assert response.status_code == 302
    assert response.headers["location"] == f"{FRONTEND_URL}/login?error=account_exists"
    assert client.cookies.get(ACCESS_TOKEN_COOKIE_NAME) is None
    assert db.query(User).filter_by(email=IDENTITY.email).one().google_sub is None


def test_callback_rejects_state_mismatch(client, db, google_enabled, exchange_returns):
    exchange_returns(IDENTITY)

    response = _callback(client, cookie_state="some-other-state")

    assert response.headers["location"] == f"{FRONTEND_URL}/login?error=google_failed"
    assert client.cookies.get(ACCESS_TOKEN_COOKIE_NAME) is None
    assert db.query(User).count() == 0


def test_callback_rejects_missing_state_cookie(
    client, google_enabled, exchange_returns
):
    exchange_returns(IDENTITY)

    response = _callback(client, cookie_state=None)

    assert response.headers["location"] == f"{FRONTEND_URL}/login?error=google_failed"


def test_callback_handles_user_cancelling_at_google(client, google_enabled):
    response = client.get(
        GOOGLE_CALLBACK_PATH, params={"error": "access_denied"}, follow_redirects=False
    )

    assert response.headers["location"] == f"{FRONTEND_URL}/login?error=google_failed"


def test_callback_handles_failed_token_exchange(client, google_enabled, monkeypatch):
    def _raise(code):
        raise GoogleAuthError("boom")

    monkeypatch.setattr(google_auth_service, "exchange_code", _raise)

    response = _callback(client)

    assert response.headers["location"] == f"{FRONTEND_URL}/login?error=google_failed"
    assert client.cookies.get(ACCESS_TOKEN_COOKIE_NAME) is None


def test_password_login_rejected_for_google_account(
    client, google_enabled, exchange_returns
):
    exchange_returns(IDENTITY)
    _callback(client)
    client.cookies.clear()

    response = client.post(
        LOGIN_PATH, json={"email": IDENTITY.email, "password": "anything123"}
    )

    assert response.status_code == 401


def test_password_change_rejected_for_google_account(
    client, google_enabled, exchange_returns
):
    exchange_returns(IDENTITY)
    _callback(client)

    response = client.put(
        PASSWORD_PATH,
        json={"current_password": "anything123", "new_password": "newpassword123"},
    )

    assert response.status_code == 400


def test_admin_user_list_shows_auth_provider(
    client, admin_client, google_enabled, exchange_returns
):
    exchange_returns(IDENTITY)
    _callback(client)

    users = admin_client.get(USERS_PATH).json()
    providers = {user["email"]: user["auth_provider"] for user in users}

    assert providers[IDENTITY.email] == "google"
    assert providers["admin@example.com"] == "password"


def test_parse_id_token_accepts_valid_claims(google_enabled):
    identity = google_auth_service.parse_id_token(_id_token())

    assert identity == IDENTITY


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "another-client"},
        {"iss": "https://evil.example.com"},
        {"exp": int(time.time()) - 60},
        {"email_verified": False},
        {"sub": None},
    ],
)
def test_parse_id_token_rejects_bad_claims(google_enabled, overrides):
    with pytest.raises(GoogleAuthError):
        google_auth_service.parse_id_token(_id_token(**overrides))


def test_parse_id_token_rejects_garbage(google_enabled):
    with pytest.raises(GoogleAuthError):
        google_auth_service.parse_id_token("not-a-jwt")
