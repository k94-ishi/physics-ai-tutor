import asyncio
import hashlib
import os
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from physics_ai_tutor.core import security
from physics_ai_tutor.database import session as session_module
from physics_ai_tutor.database.base import Base
from physics_ai_tutor.database.dependency import get_async_db, get_db
from physics_ai_tutor.main import app
from physics_ai_tutor.models.user import User
from physics_ai_tutor.services import (
    concept_service,
    deepseek_service,
    embedding_service,
    rag_service,
    translation_service,
    user_service,
)

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpass123"
USER_EMAIL = "user@example.com"
USER_PASSWORD = "userpass123"


def _default_test_database_url() -> str:
    # Derive the database name from the checkout path so worktrees sharing
    # one postgres-test container cannot wipe each other's test schema.
    repo_root = Path(__file__).resolve().parents[2]
    suffix = hashlib.sha256(str(repo_root).encode()).hexdigest()[:8]

    return (
        "postgresql+psycopg://physics:physics@localhost:5433"
        f"/physics_ai_tutor_test_{suffix}"
    )


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or _default_test_database_url()

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"

engine = create_engine(TEST_DATABASE_URL)
# Same database, async driver: for the slices converted by Track F ([67]).
async_engine = create_async_engine(TEST_DATABASE_URL)


def _create_database_if_missing() -> None:
    url = make_url(TEST_DATABASE_URL)
    admin_engine = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )

    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        ).scalar()

        if not exists:
            # Identifier cannot be a bind parameter; the name is trusted
            # (derived from the path or an env var set by the developer).
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))

    admin_engine.dispose()


def _advisory_lock_key() -> int:
    # Advisory locks are server-wide, so scope the key to this database.
    digest = hashlib.sha256(TEST_DATABASE_URL.encode()).digest()

    return int.from_bytes(digest[:8], "big", signed=True)


def _alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI))
    # alembic.ini escapes "%" for configparser; mirror that for the URL.
    config.attributes["sqlalchemy_url"] = TEST_DATABASE_URL.replace("%", "%%")
    config.attributes["configure_logger"] = False
    return config


def create_user(db, email: str, password: str, role: str = "user"):
    """Create a user from a sync test ([73]).

    The service is async now, so the many sync tests get one bridge
    rather than each growing an event loop. The row is returned **loaded
    into the caller's session**, not detached: tests go on to mutate it
    (`user.role = "admin"; db.commit()`), which silently does nothing to
    an object whose session has closed.
    """

    async def _create():
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            created = await user_service.create_user(
                session, email, password, role=role
            )
            return created.id

    user_id = asyncio.run(_create())

    return db.get(User, user_id)


async def async_create_user(db, email: str, password: str, role: str = "user"):
    """`create_user` for a test that already runs on the event loop ([83]).

    `asyncio.run` cannot nest, so an async test awaits this one instead;
    the row is still returned loaded into the sync `db` session.
    """
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        created = await user_service.create_user(session, email, password, role=role)
        user_id = created.id

    return db.get(User, user_id)


@pytest.fixture(scope="session", autouse=True)
def _migrate_test_database():
    _create_database_if_missing()

    # Hold a session-scoped advisory lock so two concurrent pytest runs on
    # the same database fail fast instead of corrupting each other.
    lock_connection = engine.connect()
    locked = lock_connection.execute(
        text("SELECT pg_try_advisory_lock(:key)"),
        {"key": _advisory_lock_key()},
    ).scalar()

    if not locked:
        lock_connection.close()
        pytest.exit(
            "Another test run is using this database. "
            "Set TEST_DATABASE_URL to a different database.",
            returncode=2,
        )

    # Build the schema with the real migrations so drift from the models
    # shows up in tests, not only in CI's separate upgrade step.
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    command.upgrade(_alembic_config(), "head")

    yield

    lock_connection.close()


# The real hasher, captured before the session fixture swaps it for tests.
PRODUCTION_PASSWORD_HASH = security.password_hash

_reset_sql: str | None = None


def _build_reset_sql() -> str:
    """DELETE every table child-first, then restart every id sequence.

    Same end state as TRUNCATE ... RESTART IDENTITY (tests rely on ids
    starting at 1), but ~2 ms instead of ~40 ms: TRUNCATE pays a fixed
    file-level cost per table, while these tables hold a few rows ([66]).
    """
    tables = [table.name for table in reversed(Base.metadata.sorted_tables)]
    with engine.connect() as connection:
        sequences = [
            name
            for table in tables
            for (name,) in connection.execute(
                text(
                    "SELECT pg_get_serial_sequence(:table, a.attname) "
                    "FROM pg_attribute a WHERE a.attrelid = CAST(:table AS regclass) "
                    "AND a.attnum > 0 AND NOT a.attisdropped"
                ),
                {"table": table},
            )
            if name is not None
        ]
    statements = [f"DELETE FROM {table}" for table in tables]
    statements += [f"ALTER SEQUENCE {name} RESTART WITH 1" for name in sequences]
    return "; ".join(statements)


def reset_database() -> None:
    """Empty every application table; cheap enough to run before each test."""
    global _reset_sql
    if _reset_sql is None:
        _reset_sql = _build_reset_sql()
    with engine.begin() as connection:
        connection.execute(text(_reset_sql))


@pytest.fixture
def db():
    # Reset before, not after: the next test resets anyway, so a teardown
    # reset only doubled the cost ([66]).
    reset_database()

    with Session(engine) as session:
        yield session


@pytest.fixture
def anyio_backend():
    """Async tests run on asyncio only; uvicorn gives us no other loop."""
    return "asyncio"


@pytest.fixture
async def async_db():
    """The `db` fixture for converted code: same reset, async session."""
    reset_database()

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
def _cheap_password_hashing():
    """Argon2 at minimal cost in tests: ~50 ms per hash becomes ~0 ([66]).

    Production keeps `PasswordHash.recommended()`; test_security.py pins it.
    """
    original = security.password_hash
    security.password_hash = PasswordHash(
        (Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),)
    )
    yield
    security.password_hash = original


@pytest.fixture(autouse=True)
def _mock_create_embeddings(monkeypatch):
    def _fake(texts):
        return [[0.1] * 1536 for _ in texts]

    async def _fake_async(texts):
        return _fake(texts)

    monkeypatch.setattr(embedding_service, "create_embeddings", _fake)
    # Both seams, so a converted caller is mocked too ([70]).
    monkeypatch.setattr(embedding_service, "async_create_embeddings", _fake_async)


@pytest.fixture(autouse=True)
def _mock_extract_concept_names(monkeypatch):
    patch_extract_concept_names(
        monkeypatch,
        lambda question, answer, language="ja": ["概念A | concept A", "概念B"],
    )


def patch_extract_concept_names(monkeypatch, extract) -> None:
    """A plain stub on the concept-extraction seam; async only since [95]."""

    async def _async_extract(*args, **kwargs):
        return extract(*args, **kwargs)

    monkeypatch.setattr(concept_service, "async_extract_concept_names", _async_extract)


def attach_concepts(db, question_id: int, names: list[str], language: str = "ja"):
    """Attach concepts from a sync test through the async service ([95]).

    Like `create_user`, a bridge for the many sync tests; the concepts are
    returned loaded into the caller's session.
    """
    from physics_ai_tutor.models import Concept

    async def _attach():
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            concepts = await concept_service.async_attach_concepts(
                session, question_id, names, language
            )
            return [concept.id for concept in concepts]

    return [db.get(Concept, concept_id) for concept_id in asyncio.run(_attach())]


def create_ai_review(db, review):
    """Arrange an AI review row from a sync test ([106]).

    The application writes only through `async_create`; this keeps the
    many sync tests on their `db` fixture. Flushes, as the deleted sync
    repository function did; the caller commits.
    """
    from physics_ai_tutor.repositories.ai_review_repository import _new_review

    row = _new_review(review)
    db.add(row)
    db.flush()

    return row


def fake_translate(question, answer, source, target):
    # Deterministic, reversible marker so tests can assert on translations.
    return f"[{target}] {question}", f"[{target}] {answer}"


async def fake_translate_async(question, answer, source, target):
    return fake_translate(question, answer, source, target)


@pytest.fixture(autouse=True)
def _mock_translate(monkeypatch):
    # Both seams, so a converted caller is mocked too ([70]).
    monkeypatch.setattr(translation_service, "async_translate_qa", fake_translate_async)


@pytest.fixture(autouse=True)
def _background_translation_uses_test_db(monkeypatch):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    # Every background task opens its session through one helper ([59]).
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    async_factory = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    monkeypatch.setattr(session_module, "AsyncSessionLocal", async_factory)


# Rate-limit counters live in the rate_limit_hits table, which is
# truncated by the `db` fixture like every other table.


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    async def override_get_async_db():
        # A converted route gets its own session, as in production: it
        # cannot share the sync `db` object, and committed rows are what
        # a real request would see anyway.
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_async_db] = override_get_async_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(client, db):
    # A separate TestClient (own cookie jar) is required here: reusing the
    # `client` fixture directly would make admin_client/user_client share
    # one cookie jar, and whichever fixture logs in last would silently
    # overwrite the other's session in tests that request both.
    create_user(db, ADMIN_EMAIL, ADMIN_PASSWORD, role="admin")

    admin = TestClient(app)
    response = admin.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200

    return admin


@pytest.fixture
def user_client(client, db):
    create_user(db, USER_EMAIL, USER_PASSWORD, role="user")

    user = TestClient(app)
    response = user.post(
        "/api/v1/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    assert response.status_code == 200

    return user


def fake_generation(answer: str):
    """A stand-in for deepseek_service.generate_answer in ask-flow tests."""
    from physics_ai_tutor.services.deepseek_service import GenerationResult

    def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        return GenerationResult(
            content=answer,
            model="mock-model",
            prompt_tokens=11,
            completion_tokens=22,
        )

    return _generate


def patch_generation(monkeypatch, generate) -> None:
    """Install one sync stub on both DeepSeek seams ([70]).

    Converted callers await `async_generate_answer` while runs, the eval
    and concept extraction still call `generate_answer`, so a test that
    patches only one of them silently reaches the real API. Stubs stay
    plain sync callables; the adapter forwards arguments and lets
    exceptions through unchanged. [73] drops the sync line here.
    """
    monkeypatch.setattr(deepseek_service, "generate_answer", generate)

    async def _async_generate(*args, **kwargs):
        return generate(*args, **kwargs)

    monkeypatch.setattr(deepseek_service, "async_generate_answer", _async_generate)


def patch_translate_qa(monkeypatch, translate) -> None:
    """A plain stub on the translation seam ([72]); async only since [102]."""

    async def _async_translate(*args, **kwargs):
        return translate(*args, **kwargs)

    monkeypatch.setattr(translation_service, "async_translate_qa", _async_translate)


def patch_create_embeddings(monkeypatch, create) -> None:
    """As `patch_generation`, for the embedding seam ([70])."""
    monkeypatch.setattr(embedding_service, "create_embeddings", create)

    async def _async_create(*args, **kwargs):
        return create(*args, **kwargs)

    monkeypatch.setattr(embedding_service, "async_create_embeddings", _async_create)


def patch_rag_answer(monkeypatch, generate) -> None:
    """As `patch_generation`, for the RAG generation seam ([70])."""
    monkeypatch.setattr(rag_service, "generate_rag_answer", generate)

    async def _async_generate(*args, **kwargs):
        return generate(*args, **kwargs)

    monkeypatch.setattr(rag_service, "async_generate_rag_answer", _async_generate)


def patch_exchange_code(monkeypatch, exchange) -> None:
    """Install a sync stub on the Google token-exchange seam ([73]).

    The exchange is an awaited HTTP call now, so a plain `setattr` with a
    sync function makes the route await a GoogleIdentity.
    """
    from physics_ai_tutor.services import google_auth_service

    async def _async_exchange(*args, **kwargs):
        return exchange(*args, **kwargs)

    monkeypatch.setattr(google_auth_service, "exchange_code", _async_exchange)


def patch_chat_completion(monkeypatch, complete) -> None:
    """As `patch_generation`, for the plain-text completion seam ([70])."""
    monkeypatch.setattr(deepseek_service, "chat_completion", complete)

    async def _async_complete(*args, **kwargs):
        return complete(*args, **kwargs)

    monkeypatch.setattr(deepseek_service, "async_chat_completion", _async_complete)
