"""enable pgvector extension

Revision ID: 608e29badd5f
Revises: c73fa181a936
Create Date: 2026-08-09 11:50:22.324652

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "608e29badd5f"
down_revision: str | Sequence[str] | None = "c73fa181a936"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
