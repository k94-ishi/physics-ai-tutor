from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.models.user import User


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    return (await db.scalars(select(User).where(User.email == email))).first()


async def get_user_by_id(
    db: AsyncSession,
    user_id: int,
) -> User | None:
    return (await db.scalars(select(User).where(User.id == user_id))).first()


async def list_users(
    db: AsyncSession,
) -> list[User]:
    return list((await db.scalars(select(User).order_by(User.id))).all())


async def create_user(
    db: AsyncSession,
    user: User,
) -> User:
    db.add(user)
    await db.flush()

    return user


async def delete_user(
    db: AsyncSession,
    user: User,
) -> None:
    await db.delete(user)
    await db.flush()


async def get_user_by_google_sub(
    db: AsyncSession,
    google_sub: str,
) -> User | None:
    return (await db.scalars(select(User).where(User.google_sub == google_sub))).first()
