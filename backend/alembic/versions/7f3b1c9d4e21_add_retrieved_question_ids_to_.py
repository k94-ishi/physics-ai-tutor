"""add retrieved_question_ids to questions

Revision ID: 7f3b1c9d4e21
Revises: 2c62a31a9031
Create Date: 2026-08-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f3b1c9d4e21"
down_revision: str | Sequence[str] | None = "2c62a31a9031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "questions",
        sa.Column(
            "retrieved_question_ids",
            postgresql.ARRAY(sa.Integer()),
            server_default="{}",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("questions", "retrieved_question_ids")
