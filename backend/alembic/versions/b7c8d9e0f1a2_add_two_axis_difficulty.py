"""add two-axis difficulty levels to questions

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-11-01 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = (
    "question_physics_level",
    "question_math_level",
    "answer_physics_level",
    "answer_math_level",
)


def upgrade() -> None:
    """Question and answer rated separately on physics and math axes."""
    for name in COLUMNS:
        op.add_column("questions", sa.Column(name, sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    for name in reversed(COLUMNS):
        op.drop_column("questions", name)
