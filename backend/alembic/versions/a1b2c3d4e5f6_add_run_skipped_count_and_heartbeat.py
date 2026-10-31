"""add skipped_count and heartbeat_at to ai_review_runs

Revision ID: a1b2c3d4e5f6
Revises: d5e6f7a8b9c0
Create Date: 2026-11-01 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Separate skips from failures; let a run prove it is still alive."""
    op.add_column(
        "ai_review_runs",
        sa.Column("skipped_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "ai_review_runs",
        sa.Column(
            "heartbeat_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Existing rows have never heartbeaten; start them at started_at so a
    # stale 'running' row is still reaped on the next start.
    op.execute("UPDATE ai_review_runs SET heartbeat_at = started_at")


def downgrade() -> None:
    op.drop_column("ai_review_runs", "heartbeat_at")
    op.drop_column("ai_review_runs", "skipped_count")
