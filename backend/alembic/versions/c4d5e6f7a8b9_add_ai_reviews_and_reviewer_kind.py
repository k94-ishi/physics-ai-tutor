"""add ai_reviews table and reviewer_kind on question_reviews

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-10-29 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: str | Sequence[str] | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """A home for AI verdicts, kept apart from the human review history."""
    op.create_table(
        "ai_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column(
            "language", sa.String(length=10), server_default="ja", nullable=False
        ),
        sa.Column("verdict", sa.String(length=10), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "reasons",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("suggested_answer", sa.Text(), nullable=True),
        sa.Column("rubric", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_reviews_question_created",
        "ai_reviews",
        ["question_id", "created_at"],
        unique=False,
    )

    op.add_column(
        "question_reviews",
        sa.Column(
            "reviewer_kind",
            sa.String(length=10),
            server_default="human",
            nullable=False,
        ),
    )
    op.add_column(
        "question_reviews", sa.Column("policy_name", sa.String(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("question_reviews", "policy_name")
    op.drop_column("question_reviews", "reviewer_kind")
    op.drop_index("ix_ai_reviews_question_created", table_name="ai_reviews")
    op.drop_table("ai_reviews")
