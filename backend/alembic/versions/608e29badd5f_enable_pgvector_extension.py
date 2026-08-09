"""enable pgvector extension

Revision ID: 608e29badd5f
Revises: c73fa181a936
Create Date: 2026-08-09 11:50:22.324652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '608e29badd5f'
down_revision: Union[str, Sequence[str], None] = 'c73fa181a936'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE EXTENSION IF NOT EXISTS vector"
    )


def downgrade() -> None:
    op.execute(
        "DROP EXTENSION IF EXISTS vector"
    )
