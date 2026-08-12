import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.core.security import hash_password, verify_password
from physics_ai_tutor.models.user import User
from physics_ai_tutor.repositories import user_repository

logger = logging.getLogger(__name__)


def register_user(
    db: Session,
    email: str,
    password: str,
    role: str = "user",
):

    hashed_password = hash_password(password)

    user = User(
        email=email,
        hashed_password=hashed_password,
        role=role,
    )

    user_repository.create_user(db, user)

    db.commit()
    db.refresh(user)

    logger.info("User registered successfully: user_id=%s role=%s", user.id, user.role)

    return user


def get_user(
    db: Session,
    user_id: int,
) -> User | None:

    return user_repository.get_user_by_id(db, user_id)


def list_users(
    db: Session,
) -> list[User]:

    return user_repository.list_users(db)


def delete_user(
    db: Session,
    user: User,
) -> None:

    user_id = user.id

    try:
        user_repository.delete_user(db, user)
        db.commit()

        logger.info("User deleted: user_id=%s", user_id)
    except Exception:
        logger.warning("Rolling back transaction: operation=delete_user")
        db.rollback()
        raise


def change_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> bool:

    if not verify_password(current_password, user.hashed_password):
        logger.warning(
            "Password change rejected: user_id=%s reason=current_password_mismatch",
            user.id,
        )
        return False

    try:
        user.hashed_password = hash_password(new_password)
        db.commit()

        logger.info("Password changed: user_id=%s", user.id)
    except Exception:
        logger.warning("Rolling back transaction: operation=change_password")
        db.rollback()
        raise

    return True
