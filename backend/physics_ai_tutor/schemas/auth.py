from pydantic import BaseModel, EmailStr

from physics_ai_tutor.schemas.token import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CurrentUser(BaseModel):
    id: int
    role: UserRole
