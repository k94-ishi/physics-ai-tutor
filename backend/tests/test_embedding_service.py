import pytest
from openai import OpenAIError

from physics_ai_tutor.core.exceptions import EmbeddingGenerationError
from physics_ai_tutor.models import Question
from physics_ai_tutor.schemas.embedding import SimilarQuestionResponse
from physics_ai_tutor.services import embedding_service
from physics_ai_tutor.services.embedding_service import (
    create_embeddings as real_create_embeddings,
)


class _FakeOpenAIError(OpenAIError):
    pass


def test_search_similar_questions_calls_create_embeddings_with_query(db, monkeypatch):
    calls = []

    def fake_create_embeddings(texts):
        calls.append(texts)
        return [[0.1] * 1536]

    monkeypatch.setattr(embedding_service, "create_embeddings", fake_create_embeddings)
    monkeypatch.setattr(
        embedding_service,
        "search_similar_embeddings",
        lambda **kwargs: [],
    )

    embedding_service.search_similar_questions(db, "類似質問", limit=3)

    assert calls == [["類似質問"]]


def test_search_similar_questions_returns_response_schema(db, monkeypatch):
    fake_vector = [0.1] * 1536

    monkeypatch.setattr(
        embedding_service,
        "create_embeddings",
        lambda texts: [fake_vector],
    )

    search_calls = []

    def fake_search_similar_embeddings(**kwargs):
        search_calls.append(kwargs)
        return [
            (None, Question(id=1, question="質問1", answer="回答1"), 0.1),
            (None, Question(id=2, question="質問2", answer="回答2"), 0.5),
        ]

    monkeypatch.setattr(
        embedding_service,
        "search_similar_embeddings",
        fake_search_similar_embeddings,
    )

    result = embedding_service.search_similar_questions(db, "類似質問", limit=3)

    assert search_calls == [
        {
            "db": db,
            "embedding": fake_vector,
            "embedding_type": "question",
            "limit": 3,
        }
    ]

    assert result == [
        SimilarQuestionResponse(id=1, question="質問1", answer="回答1", distance=0.1),
        SimilarQuestionResponse(id=2, question="質問2", answer="回答2", distance=0.5),
    ]


def test_create_embeddings_wraps_openai_error(monkeypatch):
    class _FakeEmbeddings:
        def create(self, **kwargs):
            raise _FakeOpenAIError("boom")

    class _FakeClient:
        embeddings = _FakeEmbeddings()

    monkeypatch.setattr(embedding_service, "client", _FakeClient())

    with pytest.raises(EmbeddingGenerationError):
        real_create_embeddings(["テキスト"])
