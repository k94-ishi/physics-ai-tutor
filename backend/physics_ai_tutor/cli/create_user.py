import argparse
import asyncio
import sys
from getpass import getpass

from pydantic import ValidationError

from physics_ai_tutor.database.database import AsyncSessionLocal
from physics_ai_tutor.repositories import user_repository
from physics_ai_tutor.schemas.token import UserRole
from physics_ai_tutor.schemas.user import UserCreate
from physics_ai_tutor.services.user_service import create_user


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a user (or admin) account.",
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=False)
    parser.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        default=UserRole.USER.value,
    )
    return parser.parse_args()


async def _create(email: str, password: str, role: str) -> None:
    """The service layer is async since [73]; the CLI awaits it."""
    async with AsyncSessionLocal() as db:
        if await user_repository.get_user_by_email(db, email) is not None:
            print(f"Email already registered: {email}", file=sys.stderr)
            sys.exit(1)

        user = await create_user(db, email, password, role=role)
        print(f"Created user: id={user.id} email={user.email} role={user.role}")


def main(email: str, password: str, role: str) -> None:
    try:
        data = UserCreate(email=email, password=password)
    except ValidationError as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(_create(data.email, data.password, role))


if __name__ == "__main__":
    args = parse_args()
    if args.password is None:
        args.password = getpass("Password: ")
    main(args.email, args.password, args.role)
