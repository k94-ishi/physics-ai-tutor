"""Engines and session factories.

Two stacks coexist while Track F ([67]) converts the app slice by slice:
the original sync one, and the async one added by [69]. Both speak to the
same database through the same psycopg driver and the same
`DATABASE_URL`; only the calling style differs. [73] retires the sync
engine from the app, leaving it to the CLIs and Alembic.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from physics_ai_tutor.core.config import settings

# Both pools are sized explicitly rather than left at SQLAlchemy's
# defaults (5 + 10), because during the migration they add up against one
# connection limit; [74] tunes the final numbers for the Supabase pooler.
POOL_SIZE = 5
MAX_OVERFLOW = 10

engine = create_engine(
    settings.database_url,
    hide_parameters=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    # A pooled connection dropped by the server is detected on checkout
    # instead of failing the request that happens to pick it up.
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

async_engine = create_async_engine(
    settings.database_url,
    hide_parameters=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_pre_ping=True,
)

# `expire_on_commit=False` as above: services return ORM objects whose
# attributes are read after the commit, and an async refresh would need
# an await the caller cannot give.
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
