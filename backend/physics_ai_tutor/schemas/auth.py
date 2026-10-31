from pydantic import BaseModel, EmailStr

from physics_ai_tutor.schemas.token import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CurrentUser(BaseModel):
    id: int
    role: UserRole


class AuthProviders(BaseModel):
    """Which login methods the frontend should offer."""

    password: bool
    google: bool
