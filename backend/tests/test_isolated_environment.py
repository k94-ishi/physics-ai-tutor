"""The test run cannot reach a real database or API ([113])."""

import os
import re
from pathlib import Path

from sqlalchemy import make_url

from physics_ai_tutor.core import deepseek, openai
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database import database
from tests import isolated_environment
from tests.conftest import TEST_DATABASE_URL

COMPOSE_FILE = Path(__file__).resolve().parents[2] / "docker-compose.yml"


def test_the_app_engine_points_at_the_test_database():
    # Whatever backend/.env says, the app's own engine uses the test database.
    assert settings.database_url == TEST_DATABASE_URL
    assert os.environ["DATABASE_URL"] == TEST_DATABASE_URL
    app_url, test_url = database.async_engine.url, make_url(TEST_DATABASE_URL)
    assert (app_url.host, app_url.port, app_url.database) == (
        test_url.host,
        test_url.port,
        test_url.database,
    )


def test_llm_clients_hold_fake_keys_and_a_dead_address():
    forced = isolated_environment.FORCED_SETTINGS
    assert settings.openai_api_key == forced["OPENAI_API_KEY"]
    assert settings.deepseek_api_key == forced["DEEPSEEK_API_KEY"]
    for client in (openai.async_client, deepseek.async_client):
        assert str(client.base_url).startswith("http://127.0.0.1:9")


def test_the_temporary_database_uses_the_compose_image():
    """Tests and `docker compose` must run the same server."""
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    block = compose.split("postgres-test:", 1)[1]
    image = re.search(r"image:\s*(\S+)", block)

    assert image is not None
    assert image.group(1) == isolated_environment.POSTGRES_IMAGE
