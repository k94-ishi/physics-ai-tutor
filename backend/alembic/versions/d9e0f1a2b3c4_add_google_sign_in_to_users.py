"""add Google Sign-In columns to users

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-10-27 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9e0f1a2b3c4"
down_revision: str | Sequence[str] | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow password-less Google accounts; existing rows stay password-based."""
    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            sa.String(),
            server_default="password",
            nullable=False,
        ),
    )
    op.add_column("users", sa.Column("google_sub", sa.String(), nullable=True))
    op.create_index(op.f("ix_users_google_sub"), "users", ["google_sub"], unique=True)
    op.alter_column(
        "users", "hashed_password", existing_type=sa.String(), nullable=True
    )
    op.create_check_constraint(
        "users_password_provider",
        "users",
        "(auth_provider = 'password') = (hashed_password IS NOT NULL)",
    )
    op.create_check_constraint(
        "users_google_provider",
        "users",
        "(auth_provider = 'google') = (google_sub IS NOT NULL)",
    )


def downgrade() -> None:
    """Drop Google accounts; they cannot exist without a password."""
    op.drop_constraint("users_google_provider", "users", type_="check")
    op.drop_constraint("users_password_provider", "users", type_="check")
    op.execute("DELETE FROM users WHERE hashed_password IS NULL")
    op.alter_column(
        "users", "hashed_password", existing_type=sa.String(), nullable=False
    )
    op.drop_index(op.f("ix_users_google_sub"), table_name="users")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "auth_provider")
