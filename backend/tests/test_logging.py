import logging
import re

import pytest

from physics_ai_tutor.core.exceptions import EmbeddingGenerationError
from physics_ai_tutor.core.logging import configure_logging
from physics_ai_tutor.services import embedding_service, question_service

PATH = "/api/v1/questions"


@pytest.fixture
def _restore_root_level():
    root = logging.getLogger()
    original_level = root.level
    yield
    root.setLevel(original_level)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def test_configure_logging_sets_debug_in_development(_restore_root_level):
    configure_logging(environment="development")

    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_sets_info_in_production(_restore_root_level):
    configure_logging(environment="production")

    assert logging.getLogger().level == logging.INFO


def test_configure_logging_silences_third_party_sdk_loggers(_restore_root_level):
    configure_logging(environment="development")

    assert logging.getLogger("openai").level == logging.WARNING
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_request_logging_middleware_passes_through_successful_response(client):
    response = client.get(PATH)

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_request_logging_middleware_logs_request_and_response(client, caplog):
    with caplog.at_level(logging.INFO, logger="physics_ai_tutor.access"):
        response = client.get(PATH)

    assert response.status_code == 200

    messages = [record.getMessage() for record in caplog.records]

    assert any(f"Request: GET {PATH}" in m for m in messages)

    response_messages = [m for m in messages if f"Response: GET {PATH}" in m]
    assert len(response_messages) == 1
    assert re.search(r"200 \d+\.\d{2}ms", response_messages[0])


def test_request_logging_middleware_logs_handled_exception_without_duplicate_error(
    client, monkeypatch, caplog
):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    with caplog.at_level(logging.INFO):
        response = client.post(
            PATH,
            json={"question": "質問", "answer": "回答"},
        )

    assert response.status_code == 503

    access_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "physics_ai_tutor.access"
    ]
    error_records = [
        record for record in caplog.records if record.levelno >= logging.ERROR
    ]

    response_access_logs = [m for m in access_messages if f"Response: POST {PATH}" in m]
    assert len(response_access_logs) == 1
    assert "503" in response_access_logs[0]

    assert len(error_records) == 1
    assert "Embedding generation failed" in error_records[0].getMessage()


def test_request_logging_middleware_logs_unhandled_exception(
    client, monkeypatch, caplog
):
    def _raise(db):
        raise RuntimeError("boom")

    monkeypatch.setattr(question_service, "fetch_questions", _raise)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            client.get(PATH)

    error_records = [
        record
        for record in caplog.records
        if record.name == "physics_ai_tutor.access" and record.levelno >= logging.ERROR
    ]

    assert len(error_records) == 1
    assert "Unhandled exception" in error_records[0].getMessage()
