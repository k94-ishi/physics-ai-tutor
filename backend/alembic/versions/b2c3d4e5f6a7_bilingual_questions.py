"""store Japanese and English text on the same question row

Revision ID: b2c3d4e5f6a7
Revises: a1d2e3f4b5c6
Create Date: 2026-10-25 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1d2e3f4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add per-language text columns; existing text becomes Japanese."""
    # questions
    op.alter_column(
        "questions",
        "question",
        new_column_name="question_ja",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "questions",
        "answer",
        new_column_name="answer_ja",
        existing_type=sa.Text(),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "questions",
        "language",
        new_column_name="original_language",
        existing_type=sa.String(length=10),
        existing_server_default="ja",
        existing_nullable=False,
    )
    op.add_column(
        "questions", sa.Column("ja_provenance", sa.String(length=10), nullable=True)
    )
    op.add_column("questions", sa.Column("question_en", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("answer_en", sa.Text(), nullable=True))
    op.add_column(
        "questions", sa.Column("en_provenance", sa.String(length=10), nullable=True)
    )
    op.execute("UPDATE questions SET ja_provenance = 'ORIGINAL'")
    op.create_check_constraint(
        "questions_has_text",
        "questions",
        "question_ja IS NOT NULL OR question_en IS NOT NULL",
    )
    op.create_check_constraint(
        "questions_ja_pair", "questions", "(question_ja IS NULL) = (answer_ja IS NULL)"
    )
    op.create_check_constraint(
        "questions_en_pair", "questions", "(question_en IS NULL) = (answer_en IS NULL)"
    )

    # question_embeddings
    op.add_column(
        "question_embeddings",
        sa.Column(
            "language", sa.String(length=10), server_default="ja", nullable=False
        ),
    )
    op.create_index(
        op.f("ix_question_embeddings_language"),
        "question_embeddings",
        ["language"],
        unique=False,
    )

    # concepts
    op.drop_constraint("concepts_name_key", "concepts", type_="unique")
    op.alter_column(
        "concepts",
        "name",
        new_column_name="name_ja",
        existing_type=sa.String(length=255),
        existing_nullable=False,
        nullable=True,
    )
    op.add_column(
        "concepts", sa.Column("name_en", sa.String(length=255), nullable=True)
    )
    op.create_unique_constraint("concepts_name_ja_key", "concepts", ["name_ja"])
    op.create_unique_constraint("concepts_name_en_key", "concepts", ["name_en"])

    # question_reviews
    op.add_column(
        "question_reviews",
        sa.Column(
            "language", sa.String(length=10), server_default="ja", nullable=False
        ),
    )


def downgrade() -> None:
    """Drop English columns; Japanese text becomes the only text again."""
    op.drop_column("question_reviews", "language")

    op.drop_constraint("concepts_name_en_key", "concepts", type_="unique")
    op.drop_constraint("concepts_name_ja_key", "concepts", type_="unique")
    op.drop_column("concepts", "name_en")
    op.alter_column(
        "concepts",
        "name_ja",
        new_column_name="name",
        existing_type=sa.String(length=255),
        existing_nullable=True,
        nullable=False,
    )
    op.create_unique_constraint("concepts_name_key", "concepts", ["name"])

    op.drop_index(
        op.f("ix_question_embeddings_language"), table_name="question_embeddings"
    )
    op.drop_column("question_embeddings", "language")

    op.drop_constraint("questions_en_pair", "questions", type_="check")
    op.drop_constraint("questions_ja_pair", "questions", type_="check")
    op.drop_constraint("questions_has_text", "questions", type_="check")
    # Rows that only have English text cannot survive the downgrade.
    op.execute("DELETE FROM questions WHERE question_ja IS NULL")
    op.drop_column("questions", "en_provenance")
    op.drop_column("questions", "answer_en")
    op.drop_column("questions", "question_en")
    op.drop_column("questions", "ja_provenance")
    op.alter_column(
        "questions",
        "original_language",
        new_column_name="language",
        existing_type=sa.String(length=10),
        existing_server_default="ja",
        existing_nullable=False,
    )
    op.alter_column(
        "questions",
        "answer_ja",
        new_column_name="answer",
        existing_type=sa.Text(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "questions",
        "question_ja",
        new_column_name="question",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
        nullable=False,
    )
