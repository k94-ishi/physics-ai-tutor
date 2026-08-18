import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.core.security import verify_password
from physics_ai_tutor.repositories import user_repository

logger = logging.getLogger(__name__)


def authenticate_user(
    db: Session,
    email: str,
    password: str,
):
    user = user_repository.get_user_by_email(
        db,
        email,
    )

    if user is None:
        logger.warning("Login failed: reason=user_not_found")
        return None

    if not verify_password(
        password,
        user.hashed_password,
    ):
        logger.warning("Login failed: user_id=%s reason=password_mismatch", user.id)
        return None

    logger.info("Login success: user_id=%s role=%s", user.id, user.role)

    return user
