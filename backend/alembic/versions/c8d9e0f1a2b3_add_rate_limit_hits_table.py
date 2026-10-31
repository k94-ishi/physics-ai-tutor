"""add rate_limit_hits table

Revision ID: c8d9e0f1a2b3
Revises: b2c3d4e5f6a7
Create Date: 2026-10-27 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist rate-limit hits so counters survive restarts."""
    op.create_table(
        "rate_limit_hits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("bucket_key", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rate_limit_hits_window",
        "rate_limit_hits",
        ["action", "bucket_key", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_rate_limit_hits_window", table_name="rate_limit_hits")
    op.drop_table("rate_limit_hits")
