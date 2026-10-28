"""add reason code to question_reviews

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-10-28 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Label why a review rejected or edited an answer."""
    op.add_column(
        "question_reviews",
        sa.Column("reason", sa.String(length=30), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("question_reviews", "reason")
