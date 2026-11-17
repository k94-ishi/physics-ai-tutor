from tests import isolated_environment

# Before any app import: the settings are read once, at import ([113]).
TEST_DATABASE_URL = isolated_environment.prepare()

import asyncio
import hashlib
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
from sqlalchemy.orm import Session

from alembic import command
from physics_ai_tutor.core import security
from physics_ai_tutor.database import session as session_module
from physics_ai_tutor.database.base import Base
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.main import app
from physics_ai_tutor.models.user import User
from physics_ai_tutor.schemas.language import Language
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
    engine.dispose()
    # Removed here, while pytest's logging still works ([113]).
    isolated_environment.stop()


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

    monkeypatch.setattr(embedding_service, "create_embeddings", _fake_async)


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

    monkeypatch.setattr(concept_service, "extract_concept_names", _async_extract)


def attach_concepts(db, question_id: int, names: list[str], language: str = "ja"):
    """Attach concepts from a sync test through the async service ([95]).

    Like `create_user`, a bridge for the many sync tests; the concepts are
    returned loaded into the caller's session.
    """
    from physics_ai_tutor.models import Concept

    async def _attach():
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            concepts = await concept_service.attach_concepts(
                session, question_id, names, language
            )
            return [concept.id for concept in concepts]

    return [db.get(Concept, concept_id) for concept_id in asyncio.run(_attach())]


def create_question(
    db,
    texts=None,
    original_language=Language.JA,
    status="APPROVED",
    source="MANUAL",
    retrieved_question_ids=None,
    provenances=None,
    question=None,
    answer=None,
    language=Language.JA,
):
    """Arrange a question row from a sync test ([111]).

    The app writes only through `create_question`; this keeps the
    many sync tests on their `db` fixture, including the legacy
    single-language `question=/answer=` form. Flushes; the caller commits.
    """
    from physics_ai_tutor.repositories.question_repository import _new_question

    if texts is None:
        if question is None or answer is None:
            raise ValueError("Either texts or question and answer are required")
        texts = {Language(language): (question, answer)}
        original_language = language

    row = _new_question(
        texts, original_language, status, source, retrieved_question_ids, provenances
    )
    db.add(row)
    db.flush()

    return row


def create_concept(
    db,
    embedding,
    extraction_model,
    embedding_model,
    extraction_prompt_version,
    name_ja=None,
    name_en=None,
    name=None,
):
    """Arrange a concept sense from a sync test ([112]).

    The app creates senses through `concept_sense_service`; this keeps the
    legacy single-name form (`name=` means Japanese). Flushes only.
    """
    from physics_ai_tutor.repositories.concept_repository import build

    concept = build(
        embedding,
        extraction_model,
        embedding_model,
        extraction_prompt_version,
        name_ja=name if name is not None else name_ja,
        name_en=name_en,
    )
    db.add(concept)
    db.flush()

    return concept


def link_concept(db, question_id, concept_id):
    """Arrange a question-concept link from a sync test; idempotent ([112])."""
    from physics_ai_tutor.models import QuestionConcept

    exists = db.get(QuestionConcept, (question_id, concept_id))
    if exists is None:
        db.add(QuestionConcept(question_id=question_id, concept_id=concept_id))
        db.flush()


def create_embedding(
    db, question_id, embedding, embedding_type, model, chunk_index=None, language="ja"
):
    """Arrange a question embedding from a sync test ([112])."""
    from physics_ai_tutor.repositories.embedding_repository import _new_embedding

    row = _new_embedding(
        question_id, embedding, embedding_type, model, chunk_index, language
    )
    db.add(row)
    db.flush()

    return row


def concepts_for_question(db, question_id):
    """Read a question's concepts from a sync test ([112])."""
    from physics_ai_tutor.repositories.question_concept_repository import (
        _concepts_for_question_select,
    )

    return list(db.scalars(_concepts_for_question_select(question_id)).all())


def create_ai_review(db, review):
    """Arrange an AI review row from a sync test ([106]).

    The application writes only through `create`; this keeps the
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
    monkeypatch.setattr(translation_service, "translate_qa", fake_translate_async)


@pytest.fixture(autouse=True)
def _background_translation_uses_test_db(monkeypatch):
    # Every background task opens its session through one helper ([59]).
    async_factory = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    monkeypatch.setattr(session_module, "AsyncSessionLocal", async_factory)


# Rate-limit counters live in the rate_limit_hits table, which is
# truncated by the `db` fixture like every other table.


@pytest.fixture
def client(db):
    async def override_get_db():
        # Each request gets its own session, as in production: it cannot
        # share the sync `db` object, and committed rows are what a real
        # request would see anyway.
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            yield session

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

    def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        return GenerationResult(
            content=answer,
            model="mock-model",
            prompt_tokens=11,
            completion_tokens=22,
        )

    return _generate


def patch_generation(monkeypatch, generate) -> None:
    """Install a plain sync stub on the DeepSeek generation seam ([70]).

    The app only awaits `generate_answer` since [108]. Stubs stay
    plain sync callables; the adapter forwards arguments and lets
    exceptions through unchanged.
    """

    async def _async_generate(*args, **kwargs):
        return generate(*args, **kwargs)

    monkeypatch.setattr(deepseek_service, "generate_answer", _async_generate)


def patch_translate_qa(monkeypatch, translate) -> None:
    """A plain stub on the translation seam ([72]); async only since [102]."""

    async def _async_translate(*args, **kwargs):
        return translate(*args, **kwargs)

    monkeypatch.setattr(translation_service, "translate_qa", _async_translate)


def patch_create_embeddings(monkeypatch, create) -> None:
    """As `patch_generation`, for the embedding seam ([70])."""

    async def _async_create(*args, **kwargs):
        return create(*args, **kwargs)

    monkeypatch.setattr(embedding_service, "create_embeddings", _async_create)


def patch_rag_answer(monkeypatch, generate) -> None:
    """As `patch_generation`, for the RAG generation seam ([70])."""

    async def _async_generate(*args, **kwargs):
        return generate(*args, **kwargs)

    monkeypatch.setattr(rag_service, "generate_rag_answer", _async_generate)


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

    async def _async_complete(*args, **kwargs):
        return complete(*args, **kwargs)

    monkeypatch.setattr(deepseek_service, "chat_completion", _async_complete)
