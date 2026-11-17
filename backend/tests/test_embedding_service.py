import pytest
from openai import OpenAIError

from physics_ai_tutor.core.exceptions import EmbeddingGenerationError
from physics_ai_tutor.models import Question
from physics_ai_tutor.schemas.embedding import SimilarQuestionResponse
from physics_ai_tutor.services import embedding_service
from physics_ai_tutor.services.embedding_service import (
    create_embeddings as real_create_embeddings,
)
from tests.conftest import patch_create_embeddings


class _FakeOpenAIError(OpenAIError):
    pass


async def _no_results(**kwargs):
    return []


@pytest.mark.anyio
async def test_search_similar_questions_calls_create_embeddings_with_query(
    async_db, monkeypatch
):
    calls = []

    def fake_create_embeddings(texts):
        calls.append(texts)
        return [[0.1] * 1536]

    patch_create_embeddings(monkeypatch, fake_create_embeddings)
    monkeypatch.setattr(embedding_service, "search_similar_embeddings", _no_results)

    await embedding_service.search_similar_questions(async_db, "類似質問", limit=3)

    assert calls == [["類似質問"]]


@pytest.mark.anyio
async def test_search_similar_questions_returns_response_schema(async_db, monkeypatch):
    fake_vector = [0.1] * 1536

    patch_create_embeddings(monkeypatch, lambda texts: [fake_vector])

    search_calls = []

    async def fake_search_similar_embeddings(**kwargs):
        search_calls.append(kwargs)
        return [
            (None, Question(id=1, question_ja="質問1", answer_ja="回答1"), 0.1),
            (None, Question(id=2, question_ja="質問2", answer_ja="回答2"), 0.5),
        ]

    monkeypatch.setattr(
        embedding_service,
        "search_similar_embeddings",
        fake_search_similar_embeddings,
    )

    result = await embedding_service.search_similar_questions(
        async_db, "類似質問", limit=3
    )

    assert search_calls == [
        {
            "db": async_db,
            "embedding": fake_vector,
            "embedding_type": "question",
            "limit": 3,
            "exclude_statuses": None,
            "language": "ja",
        }
    ]

    assert result == [
        SimilarQuestionResponse(
            id=1, question="質問1", answer="回答1", language="ja", distance=0.1
        ),
        SimilarQuestionResponse(
            id=2, question="質問2", answer="回答2", language="ja", distance=0.5
        ),
    ]


@pytest.mark.anyio
async def test_create_embeddings_wraps_openai_error(monkeypatch):
    class _FakeEmbeddings:
        async def create(self, **kwargs):
            raise _FakeOpenAIError("boom")

    class _FakeClient:
        embeddings = _FakeEmbeddings()

    monkeypatch.setattr(embedding_service, "async_client", _FakeClient())

    with pytest.raises(EmbeddingGenerationError):
        await real_create_embeddings(["テキスト"])


# --- batching ([76]) ----------------------------------------------------------


def test_chunks_split_by_count_and_by_total_length(monkeypatch):
    monkeypatch.setattr(embedding_service, "EMBED_BATCH_MAX_ITEMS", 3)
    monkeypatch.setattr(embedding_service, "EMBED_BATCH_MAX_CHARS", 10)

    by_count = embedding_service._chunks(["a", "b", "c", "d", "e", "f", "g"])
    assert by_count == [["a", "b", "c"], ["d", "e", "f"], ["g"]]

    by_length = embedding_service._chunks(["xxxx", "yyyy", "zzzz", "w"])
    assert by_length == [["xxxx", "yyyy"], ["zzzz", "w"]]

    # One oversized text still travels, alone.
    assert embedding_service._chunks(["x" * 50, "a"]) == [["x" * 50], ["a"]]
    assert embedding_service._chunks([]) == []


@pytest.mark.anyio
async def test_async_embed_many_keeps_input_order_across_chunks(monkeypatch):
    monkeypatch.setattr(embedding_service, "EMBED_BATCH_MAX_ITEMS", 2)
    calls = []

    def fake_create_embeddings(texts):
        calls.append(list(texts))
        # A vector that names its text, so a shuffle would be visible.
        return [[float(len(text))] for text in texts]

    patch_create_embeddings(monkeypatch, fake_create_embeddings)

    vectors = await embedding_service.embed_many(["a", "bb", "ccc", "dddd", "eeeee"])

    assert vectors == [[1.0], [2.0], [3.0], [4.0], [5.0]]
    assert calls == [["a", "bb"], ["ccc", "dddd"], ["eeeee"]]
