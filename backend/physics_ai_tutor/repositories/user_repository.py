from sqlalchemy.orm import Session

from physics_ai_tutor.models.user import User


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:

    return (
        db.query(User)
        .filter(User.email == email)
        .first()
    )


def get_user_by_id(
    db: Session,
    user_id: int,
) -> User | None:

    return (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )


def list_users(
    db: Session,
) -> list[User]:

    return db.query(User).order_by(User.id).all()


def create_user(
    db: Session,
    user: User,
) -> User:

    db.add(user)
    db.flush()

    return user


def delete_user(
    db: Session,
    user: User,
) -> None:

    db.delete(user)
    db.flush()
