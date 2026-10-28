"""add generation metadata to questions

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-10-28 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: str | Sequence[str] | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record which model, prompt, and mode produced each AI answer."""
    op.add_column(
        "questions", sa.Column("generation_model", sa.String(), nullable=True)
    )
    op.add_column(
        "questions", sa.Column("prompt_version", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "questions", sa.Column("generation_mode", sa.String(length=10), nullable=True)
    )
    op.add_column("questions", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column(
        "questions", sa.Column("completion_tokens", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("questions", "completion_tokens")
    op.drop_column("questions", "prompt_tokens")
    op.drop_column("questions", "generation_mode")
    op.drop_column("questions", "prompt_version")
    op.drop_column("questions", "generation_model")
