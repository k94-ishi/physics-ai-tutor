"""concept senses with many terms per language

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-11-10 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2f3a4b5c6d7"
down_revision: str | Sequence[str] | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Same normalisation as concept_service.normalize_term, in SQL.
_NORMALIZE = "lower(btrim(regexp_replace(normalize({col}, NFKC), '\\s+', ' ', 'g')))"


def upgrade() -> None:
    """A concept becomes a sense; its words move to concept_terms ([55]).

    Additive: name_ja/name_en stay as mirrors of the preferred terms, only
    their uniqueness is dropped so two senses may share a word.
    """
    op.add_column("concepts", sa.Column("gloss_ja", sa.String(255), nullable=True))
    op.add_column("concepts", sa.Column("gloss_en", sa.String(255), nullable=True))

    op.create_table(
        "concept_terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "concept_id",
            sa.Integer(),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("term", sa.String(255), nullable=False),
        sa.Column("normalized", sa.String(255), nullable=False),
        sa.Column(
            "is_preferred",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("source", sa.String(20), server_default="EXTRACTED", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "concept_id", "language", "normalized", name="uq_concept_terms_sense_word"
        ),
    )
    op.create_index("ix_concept_terms_concept_id", "concept_terms", ["concept_id"])
    op.create_index(
        "ix_concept_terms_lookup", "concept_terms", ["language", "normalized"]
    )
    op.create_index(
        "uq_concept_terms_one_preferred",
        "concept_terms",
        ["concept_id", "language"],
        unique=True,
        postgresql_where=sa.text("is_preferred"),
    )

    for lang in ("ja", "en"):
        col = f"name_{lang}"
        op.execute(
            f"INSERT INTO concept_terms "
            f"(concept_id, language, term, normalized, is_preferred, source) "
            f"SELECT id, '{lang}', {col}, {_NORMALIZE.format(col=col)}, true, "
            f"'EXTRACTED' FROM concepts WHERE {col} IS NOT NULL"
        )

    op.drop_constraint("concepts_name_ja_key", "concepts", type_="unique")
    op.drop_constraint("concepts_name_en_key", "concepts", type_="unique")


def downgrade() -> None:
    """Restores 1:1 names. Fails if two senses now share a preferred name;
    merge them in the admin editor first."""
    op.create_unique_constraint("concepts_name_en_key", "concepts", ["name_en"])
    op.create_unique_constraint("concepts_name_ja_key", "concepts", ["name_ja"])
    op.drop_index("uq_concept_terms_one_preferred", table_name="concept_terms")
    op.drop_index("ix_concept_terms_lookup", table_name="concept_terms")
    op.drop_index("ix_concept_terms_concept_id", table_name="concept_terms")
    op.drop_table("concept_terms")
    op.drop_column("concepts", "gloss_en")
    op.drop_column("concepts", "gloss_ja")
