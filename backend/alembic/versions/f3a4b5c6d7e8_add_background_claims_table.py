"""add background_claims table

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-11-12 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: str | Sequence[str] | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Claim background work in the database so two workers cannot share it."""
    op.create_table(
        "background_claims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("key", sa.Integer(), nullable=False),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        # The guard itself: one worker per piece of work.
        sa.UniqueConstraint("kind", "key", name="uq_background_claims_work"),
    )
    # Sweeping expired claims scans by age.
    op.create_index(
        "ix_background_claims_claimed_at",
        "background_claims",
        ["claimed_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the claims; in-flight background work simply redoes itself."""
    op.drop_index("ix_background_claims_claimed_at", table_name="background_claims")
    op.drop_table("background_claims")
