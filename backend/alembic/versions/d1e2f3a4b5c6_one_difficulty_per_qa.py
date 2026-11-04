"""one difficulty rating per QA pair

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-11-04 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The answer rating ("what a reader needs to follow it") becomes the
    rating of the QA pair; the separate question rating is dropped ([40],
    owner's decision 2026-11-04)."""
    op.alter_column(
        "questions", "answer_physics_level", new_column_name="physics_level"
    )
    op.alter_column("questions", "answer_math_level", new_column_name="math_level")
    op.drop_column("questions", "question_physics_level")
    op.drop_column("questions", "question_math_level")


def downgrade() -> None:
    op.add_column(
        "questions", sa.Column("question_math_level", sa.SmallInteger(), nullable=True)
    )
    op.add_column(
        "questions",
        sa.Column("question_physics_level", sa.SmallInteger(), nullable=True),
    )
    op.alter_column("questions", "math_level", new_column_name="answer_math_level")
    op.alter_column(
        "questions", "physics_level", new_column_name="answer_physics_level"
    )
