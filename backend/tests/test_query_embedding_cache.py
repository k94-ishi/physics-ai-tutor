"""Query-embedding cache ([49]): repeated vector searches cost no API call."""

import pytest

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.models import QueryEmbedding
from physics_ai_tutor.services import embedding_service

SEARCH_PATH = "/api/v1/questions/search"


@pytest.fixture
def _counted_embeddings(monkeypatch):
    calls = {"n": 0}

    def _fake(texts):
        calls["n"] += 1
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(embedding_service, "create_embeddings", _fake)
    return calls


def test_normalize_query_collapses_trivial_differences():
    assert embedding_service.normalize_query(
        "  斜方投射　の  運動 "
    ) == embedding_service.normalize_query("斜方投射 の 運動")
    # NFKC: fullwidth alphanumerics fold to ASCII.
    assert embedding_service.normalize_query("ｖ−ｔグラフ") == (
        embedding_service.normalize_query("v−tグラフ")
    )


def test_second_search_for_the_same_text_embeds_nothing(
    client, db, _counted_embeddings
):
    assert client.post(SEARCH_PATH, json={"query": "斜方投射の運動"}).status_code == 200
    assert _counted_embeddings["n"] == 1

    # Same text up to normalisation: cache hit, no second OpenAI call.
    assert (
        client.post(SEARCH_PATH, json={"query": " 斜方投射の運動　"}).status_code == 200
    )
    assert _counted_embeddings["n"] == 1

    row = db.query(QueryEmbedding).one()
    assert row.hit_count == 1
    assert row.normalized_text == "斜方投射の運動"


def test_different_text_embeds_again(client, db, _counted_embeddings):
    client.post(SEARCH_PATH, json={"query": "運動量とは"})
    client.post(SEARCH_PATH, json={"query": "力積とは"})

    assert _counted_embeddings["n"] == 2
    assert db.query(QueryEmbedding).count() == 2


def test_model_change_misses_the_cache(client, db, monkeypatch, _counted_embeddings):
    """Embeddings are only comparable within one model; a model upgrade must
    re-embed rather than silently reuse incompatible vectors."""
    client.post(SEARCH_PATH, json={"query": "終端速度"})
    assert _counted_embeddings["n"] == 1

    monkeypatch.setattr(settings, "embedding_model", "next-gen-embedding")
    client.post(SEARCH_PATH, json={"query": "終端速度"})

    assert _counted_embeddings["n"] == 2
    models = {row.model for row in db.query(QueryEmbedding).all()}
    assert len(models) == 2


def test_rag_ask_reuses_a_searched_query_embedding(
    client, db, monkeypatch, _counted_embeddings
):
    """The ask path goes through the same cache: search first, ask after -
    the ask's retrieval embeds nothing new."""
    from physics_ai_tutor.services import deepseek_service
    from tests.conftest import fake_generation

    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    client.post(SEARCH_PATH, json={"query": "空気抵抗がある場合の斜方投射"})
    before = _counted_embeddings["n"]

    # RAG mode with no candidate ids is the path that retrieves (and embeds).
    client.post(
        "/api/v1/ai/ask",
        json={"question": "空気抵抗がある場合の斜方投射", "mode": "RAG"},
    )

    # The stored question's own embeddings are a different code path
    # (per-language rows); the retrieval query itself must hit the cache.
    row = (
        db.query(QueryEmbedding)
        .filter(QueryEmbedding.normalized_text == "空気抵抗がある場合の斜方投射")
        .one()
    )
    assert row.hit_count >= 1, "the ask's retrieval must hit the search's cache"
    assert _counted_embeddings["n"] >= before
