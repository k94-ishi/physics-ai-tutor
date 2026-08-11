import time
import uuid

import jwt as pyjwt

from physics_ai_tutor.api.dependencies import ACCESS_TOKEN_COOKIE_NAME
from physics_ai_tutor.core.config import settings

REGISTER_PATH = "/api/v1/auth/register"
LOGIN_PATH = "/api/v1/auth/login"
LOGOUT_PATH = "/api/v1/auth/logout"
ME_PATH = "/api/v1/users/me"

EMAIL = "auth-test@example.com"
PASSWORD = "testpassword123"


def _make_token(
    *,
    sub: str,
    role: str = "user",
    exp_delta_seconds: int,
    jti: str | None = None,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "role": role,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + exp_delta_seconds,
        "jti": jti or str(uuid.uuid4()),
    }
    return pyjwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def _register(client, email=EMAIL, password=PASSWORD):
    return client.post(REGISTER_PATH, json={"email": email, "password": password})


def test_register_success(client):
    response = _register(client)

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == EMAIL
    assert data["role"] == "user"
    assert "hashed_password" not in data


def test_register_duplicate_email_rejected(client):
    _register(client)

    response = _register(client)

    assert response.status_code == 409


def test_login_success_sets_cookie(client):
    _register(client)

    response = client.post(LOGIN_PATH, json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["email"] == EMAIL

    set_cookie = response.headers.get("set-cookie")

    assert set_cookie is not None
    assert f"{ACCESS_TOKEN_COOKIE_NAME}=" in set_cookie
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()


def test_login_wrong_password_rejected(client):
    _register(client)

    response = client.post(
        LOGIN_PATH, json={"email": EMAIL, "password": "wrongpassword"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_unknown_email_rejected(client):
    response = client.post(
        LOGIN_PATH, json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_logout_clears_cookie_without_prior_login(client):
    response = client.post(LOGOUT_PATH)

    assert response.status_code == 204

    set_cookie = response.headers.get("set-cookie")

    assert set_cookie is not None
    assert ACCESS_TOKEN_COOKIE_NAME in set_cookie
    assert "max-age=0" in set_cookie.lower()


def test_logout_then_protected_request_is_unauthenticated(client):
    _register(client)
    client.post(LOGIN_PATH, json={"email": EMAIL, "password": PASSWORD})

    assert client.get(ME_PATH).status_code == 200

    client.post(LOGOUT_PATH)

    assert client.get(ME_PATH).status_code == 401


def test_missing_token_rejected(client):
    response = client.get(ME_PATH)

    assert response.status_code == 401


def test_malformed_token_rejected(client):
    client.cookies.set(ACCESS_TOKEN_COOKIE_NAME, "not-a-real-jwt")

    response = client.get(ME_PATH)

    assert response.status_code == 401


def test_expired_token_rejected(client):
    register_response = _register(client)
    user_id = register_response.json()["id"]

    token = _make_token(sub=str(user_id), role="user", exp_delta_seconds=-60)
    client.cookies.set(ACCESS_TOKEN_COOKIE_NAME, token)

    response = client.get(ME_PATH)

    assert response.status_code == 401


def test_sliding_refresh_reissues_cookie_near_expiry(client):
    register_response = _register(client)
    user_id = register_response.json()["id"]

    original_jti = str(uuid.uuid4())
    # Below jwt_refresh_threshold_minutes (default 10min = 600s) but still valid.
    token = _make_token(
        sub=str(user_id), role="user", exp_delta_seconds=120, jti=original_jti
    )
    client.cookies.set(ACCESS_TOKEN_COOKIE_NAME, token)

    response = client.get(ME_PATH)

    assert response.status_code == 200

    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is not None

    new_token = response.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    assert new_token != token

    decoded = pyjwt.decode(
        new_token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
    )
    assert decoded["jti"] == original_jti
    assert decoded["sub"] == str(user_id)


def test_no_refresh_when_far_from_expiry(client):
    register_response = _register(client)
    user_id = register_response.json()["id"]

    token = _make_token(sub=str(user_id), role="user", exp_delta_seconds=3600)
    client.cookies.set(ACCESS_TOKEN_COOKIE_NAME, token)

    response = client.get(ME_PATH)

    assert response.status_code == 200
    assert response.headers.get("set-cookie") is None
