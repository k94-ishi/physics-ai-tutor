import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from physics_ai_tutor.database.base import Base
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.main import app
from physics_ai_tutor.services import concept_service, embedding_service
from physics_ai_tutor.services.user_service import create_user

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpass123"
USER_EMAIL = "user@example.com"
USER_PASSWORD = "userpass123"

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://physics:physics@localhost:5433/physics_ai_tutor_test",
)

engine = create_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="session", autouse=True)
def _enable_pgvector_extension():
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    
    with Session(engine) as session:
        yield session
    
    Base.metadata.drop_all(bind=engine)


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
        lambda question, answer: ["概念A", "概念B"],
    )


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
