"""Stage timing logs ([68])."""

import logging
import re

import pytest

from physics_ai_tutor.core import timing
from physics_ai_tutor.services import deepseek_service
from tests.conftest import fake_generation

LOGGER = "physics_ai_tutor.core.timing"
STAGE_LINE = re.compile(
    r"Stage finished: name=(\S+) path=(\S+) duration_ms=(\d+\.\d{2})"
)


def stage_lines(caplog):
    return [
        match
        for match in (
            STAGE_LINE.search(record.getMessage())
            for record in caplog.records
            if record.name == LOGGER
        )
        if match is not None
    ]


def test_stage_logs_name_and_duration(caplog):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        with timing.stage("vector_search"):
            pass

    lines = stage_lines(caplog)

    assert len(lines) == 1
    assert lines[0].group(1) == "vector_search"
    assert float(lines[0].group(3)) >= 0


def test_stage_reports_the_request_path(caplog):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        with timing.request_path("/api/v1/ai/ask"):
            with timing.stage("deepseek_chat"):
                pass

    assert stage_lines(caplog)[0].group(2) == "/api/v1/ai/ask"


def test_stage_outside_a_request_has_no_path(caplog):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        with timing.stage("ai_review_item"):
            pass

    assert stage_lines(caplog)[0].group(2) == "-"


def test_request_path_is_restored_afterwards(caplog):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        with timing.request_path("/outer"):
            with timing.request_path("/inner"):
                pass
            with timing.stage("after_inner"):
                pass

    assert stage_lines(caplog)[0].group(2) == "/outer"


def test_stage_logs_extra_fields(caplog):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        with timing.stage("embed_query", cache="miss") as stage:
            stage.note(count=3)

    message = caplog.records[-1].getMessage()

    assert "cache=miss" in message
    assert "count=3" in message


def test_stage_logs_a_failed_call_and_reraises(caplog):
    # A failed external call's duration is part of the latency too.
    with caplog.at_level(logging.INFO, logger=LOGGER):
        with pytest.raises(RuntimeError):
            with timing.stage("deepseek_chat"):
                raise RuntimeError("boom")

    assert stage_lines(caplog)[0].group(1) == "deepseek_chat"


def test_ask_request_emits_its_stages_under_the_request_path(
    client, monkeypatch, caplog
):
    """A cache-miss ask is explainable from its stage lines alone."""
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    with caplog.at_level(logging.INFO, logger=LOGGER):
        response = client.post(
            "/api/v1/ai/ask", json={"question": "加速度とは何ですか"}
        )

    assert response.status_code == 200

    staged = {match.group(1): match.group(2) for match in stage_lines(caplog)}

    assert staged["ask_cache_lookup"] == "/api/v1/ai/ask"
    assert staged["save_answer"] == "/api/v1/ai/ask"


def test_post_generation_stages_are_labelled_as_background(client, monkeypatch, caplog):
    """Work after the response is not charged to the request that caused it."""
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    with caplog.at_level(logging.INFO, logger=LOGGER):
        response = client.post(
            "/api/v1/ai/ask", json={"question": "加速度とは何ですか"}
        )

    assert response.status_code == 200

    staged = {match.group(1): match.group(2) for match in stage_lines(caplog)}

    assert staged["translate_qa"] == "background:post_generation"
    assert staged["embed_language"] == "background:post_generation"


def test_rag_ask_times_retrieval_and_the_query_embedding(client, monkeypatch, caplog):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/ai/ask",
            json={"question": "運動量保存則とは", "mode": "RAG"},
        )

    assert response.status_code == 200

    names = [match.group(1) for match in stage_lines(caplog)]

    assert "rag_context" in names
    assert "embed_query" in names
    assert "vector_search" in names


def _embed_query_messages(caplog) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == LOGGER and "name=embed_query" in record.getMessage()
    ]


def test_search_stage_says_whether_the_embedding_was_cached(client, db, caplog):
    """The second identical search reports a cache hit, not a miss ([49])."""
    path = "/api/v1/questions/search"

    with caplog.at_level(logging.INFO, logger=LOGGER):
        assert client.post(path, json={"query": "斜方投射の最高点"}).status_code == 200
        first = _embed_query_messages(caplog)

        caplog.clear()
        assert client.post(path, json={"query": "斜方投射の最高点"}).status_code == 200
        second = _embed_query_messages(caplog)

    assert len(first) == 1
    assert "cache=miss" in first[0]
    assert len(second) == 1
    assert "cache=hit" in second[0]
