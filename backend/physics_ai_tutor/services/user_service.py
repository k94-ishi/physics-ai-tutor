import logging

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.core.security import hash_password, verify_password
from physics_ai_tutor.database.transaction import transaction
from physics_ai_tutor.models.user import User
from physics_ai_tutor.repositories import user_repository

logger = logging.getLogger(__name__)


async def create_user(
    db: AsyncSession,
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

    async with transaction(db, "create_user"):
        await user_repository.create_user(db, user)
    await db.refresh(user)

    logger.info("User created: user_id=%s role=%s", user.id, user.role)

    return user


async def get_user(
    db: AsyncSession,
    user_id: int,
) -> User | None:

    return await user_repository.get_user_by_id(db, user_id)


async def email_registered(db: AsyncSession, email: str) -> bool:
    return await user_repository.get_user_by_email(db, email) is not None


async def list_users(
    db: AsyncSession,
) -> list[User]:

    return await user_repository.list_users(db)


async def delete_user(
    db: AsyncSession,
    user: User,
) -> None:

    user_id = user.id

    async with transaction(db, "delete_user"):
        await user_repository.delete_user(db, user)

    logger.info("User deleted: user_id=%s", user_id)


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> bool:

    if user.hashed_password is None:
        logger.warning(
            "Password change rejected: user_id=%s reason=no_password", user.id
        )
        return False

    if not verify_password(current_password, user.hashed_password):
        logger.warning(
            "Password change rejected: user_id=%s reason=current_password_mismatch",
            user.id,
        )
        return False

    async with transaction(db, "change_password"):
        user.hashed_password = hash_password(new_password)

    logger.info("Password changed: user_id=%s", user.id)
    return True
