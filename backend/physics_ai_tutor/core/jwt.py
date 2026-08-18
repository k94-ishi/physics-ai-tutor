from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.schemas.token import JWTPayload


def create_access_token(
    *,
    subject: str,
    role: str,
    jti: str | None = None,
):
    now = datetime.now(UTC)

    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = JWTPayload(
        sub=subject,
        role=role,
        iss=settings.jwt_issuer,
        exp=int(expire.timestamp()),
        iat=int(now.timestamp()),
        jti=jti or str(uuid4()),
    )

    return jwt.encode(
        payload.model_dump(),
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(
    token: str,
) -> JWTPayload:

    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
    )

    return JWTPayload.model_validate(payload)
