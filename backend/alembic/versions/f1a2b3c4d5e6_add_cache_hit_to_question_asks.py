"""add cache_hit flag to question_asks

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-10-28 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "e0f1a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record explicitly whether an ask was served from the cache."""
    op.add_column(
        "question_asks",
        sa.Column("cache_hit", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("question_asks", "cache_hit")
