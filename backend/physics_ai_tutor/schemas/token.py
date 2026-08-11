from enum import StrEnum

from pydantic import BaseModel


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class JWTPayload(BaseModel):
    sub: str
    role: UserRole
    iss: str
    exp: int
    iat: int
    jti: str
