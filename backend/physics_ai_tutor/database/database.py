"""The engine and session factory: one of each since [110].

The app runs on SQLAlchemy's async engine over the psycopg driver and the
plain `DATABASE_URL`. Alembic keeps its own sync engine for migrations;
tests build their own sync engine to arrange rows.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from physics_ai_tutor.core.config import settings

# Sized explicitly rather than left at SQLAlchemy's defaults (5 + 10), so
# the connection budget per worker is visible here; [74] tunes the numbers
# for the Supabase pooler.
POOL_SIZE = 5
MAX_OVERFLOW = 10

async_engine = create_async_engine(
    settings.database_url,
    hide_parameters=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    # A pooled connection dropped by the server is detected on checkout
    # instead of failing the request that happens to pick it up.
    pool_pre_ping=True,
)

# `expire_on_commit=False`: services return ORM objects whose attributes
# are read after the commit, and an async refresh would need an await the
# caller cannot give.
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
