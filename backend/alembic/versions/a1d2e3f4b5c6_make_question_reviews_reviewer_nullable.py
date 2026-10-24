"""make question_reviews.reviewer_id nullable with ON DELETE SET NULL

Revision ID: a1d2e3f4b5c6
Revises: 7f3b1c9d4e21
Create Date: 2026-10-24 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1d2e3f4b5c6"
down_revision: str | Sequence[str] | None = "7f3b1c9d4e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK_NAME = "question_reviews_reviewer_id_fkey"


def upgrade() -> None:
    """Allow deleting a reviewer while keeping their review history."""
    op.alter_column(
        "question_reviews",
        "reviewer_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.drop_constraint(FK_NAME, "question_reviews", type_="foreignkey")
    op.create_foreign_key(
        FK_NAME,
        "question_reviews",
        "users",
        ["reviewer_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Restore the strict foreign key (fails if orphaned reviews exist)."""
    op.drop_constraint(FK_NAME, "question_reviews", type_="foreignkey")
    op.create_foreign_key(
        FK_NAME,
        "question_reviews",
        "users",
        ["reviewer_id"],
        ["id"],
    )
    op.alter_column(
        "question_reviews",
        "reviewer_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
