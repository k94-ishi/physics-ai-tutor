from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from physics_ai_tutor.database.base import Base


class User(Base):
    """An account; either password-based (admins) or Google-based (students).

    The two kinds are kept strictly separate: a Google account is never
    linked to a password account by e-mail match, which closes a known
    account-takeover path.
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(auth_provider = 'password') = (hashed_password IS NOT NULL)",
            name="users_password_provider",
        ),
        CheckConstraint(
            "(auth_provider = 'google') = (google_sub IS NOT NULL)",
            name="users_google_provider",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    auth_provider: Mapped[str] = mapped_column(
        String, default="password", server_default="password", nullable=False
    )
    google_sub: Mapped[str | None] = mapped_column(
        String, unique=True, index=True, nullable=True
    )
    role: Mapped[str] = mapped_column(String, default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
