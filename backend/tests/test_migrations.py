from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory

from physics_ai_tutor.database.base import Base
from tests.conftest import _alembic_config, engine


def test_single_migration_head():
    heads = ScriptDirectory.from_config(_alembic_config()).get_heads()

    assert len(heads) == 1, f"Multiple Alembic heads found: {heads}"


def test_models_match_migrations(db):
    # The test schema is built by `alembic upgrade head` in conftest.
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        diff = compare_metadata(context, Base.metadata)

    assert diff == [], f"Models and migrations have drifted: {diff}"
