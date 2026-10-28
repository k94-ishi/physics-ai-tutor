import hashlib
import os
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from physics_ai_tutor.api.v1 import ai as ai_router
from physics_ai_tutor.database.base import Base
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.main import app
from physics_ai_tutor.services import (
    concept_service,
    embedding_service,
    translation_service,
)
from physics_ai_tutor.services.user_service import create_user

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


def _truncate_all_tables() -> None:
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)

    with engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def db():
    _truncate_all_tables()

    with Session(engine) as session:
        yield session

    _truncate_all_tables()


@pytest.fixture(autouse=True)
def _mock_create_embeddings(monkeypatch):
    monkeypatch.setattr(
        embedding_service,
        "create_embeddings",
        lambda texts: [[0.1] * 1536 for _ in texts],
    )


@pytest.fixture(autouse=True)
def _mock_extract_concept_names(monkeypatch):
    monkeypatch.setattr(
        concept_service,
        "extract_concept_names",
        lambda question, answer, language="ja": ["概念A | concept A", "概念B"],
    )


def fake_translate(question, answer, source, target):
    # Deterministic, reversible marker so tests can assert on translations.
    return f"[{target}] {question}", f"[{target}] {answer}"


@pytest.fixture(autouse=True)
def _mock_translate(monkeypatch):
    monkeypatch.setattr(translation_service, "translate_qa", fake_translate)


@pytest.fixture(autouse=True)
def _background_translation_uses_test_db(monkeypatch):
    # The AI router opens its own session for background translation.
    monkeypatch.setattr(
        ai_router, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False)
    )


# Rate-limit counters live in the rate_limit_hits table, which is
# truncated by the `db` fixture like every other table.


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

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

    return lambda system_prompt, user_prompt: GenerationResult(
        content=answer,
        model="mock-model",
        prompt_tokens=11,
        completion_tokens=22,
    )
