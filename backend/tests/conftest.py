import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from physics_ai_tutor.database.base import Base
from physics_ai_tutor.database.dependency import get_db
from physics_ai_tutor.main import app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://physics:physics@localhost:5433/physics_ai_tutor_test",
)

engine = create_engine(TEST_DATABASE_URL)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    
    with Session(engine) as session:
        yield session
    
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()
