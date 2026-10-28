"""add question_asks table

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-10-28 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e0f1a2b3c4d5"
down_revision: str | Sequence[str] | None = "d9e0f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record which signed-in student asked which question."""
    op.create_table(
        "question_asks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "language", sa.String(length=10), server_default="ja", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_question_asks_question_id"),
        "question_asks",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        "ix_question_asks_user_created",
        "question_asks",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the ask history."""
    op.drop_index("ix_question_asks_user_created", table_name="question_asks")
    op.drop_index(op.f("ix_question_asks_question_id"), table_name="question_asks")
    op.drop_table("question_asks")
