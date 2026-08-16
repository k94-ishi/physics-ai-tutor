from physics_ai_tutor.core.exceptions import (
    DeepSeekGenerationError,
    EmbeddingGenerationError,
)
from physics_ai_tutor.models import Question
from physics_ai_tutor.services import deepseek_service, embedding_service, rag_service

ASK_PATH = "/api/v1/ai/ask"


def test_ask_ai_returns_answer(client, monkeypatch):
    monkeypatch.setattr(
        deepseek_service,
        "chat_completion",
        lambda system_prompt, user_prompt: "加速度は単位時間あたりの速度の変化量です。",
    )

    response = client.post(ASK_PATH, json={"question": "加速度って何？"})

    assert response.status_code == 200
    assert response.json() == {"answer": "加速度は単位時間あたりの速度の変化量です。"}


def test_ask_ai_empty_question_rejected(client):
    response = client.post(ASK_PATH, json={"question": ""})

    assert response.status_code == 422


def test_ask_ai_does_not_require_authentication(client, monkeypatch):
    monkeypatch.setattr(
        deepseek_service, "chat_completion", lambda system_prompt, user_prompt: "回答"
    )

    response = client.post(ASK_PATH, json={"question": "テスト質問です"})

    assert response.status_code == 200


def test_ask_ai_failure_returns_503(client, monkeypatch):
    def _raise(system_prompt, user_prompt):
        raise DeepSeekGenerationError("boom")

    monkeypatch.setattr(deepseek_service, "chat_completion", _raise)

    response = client.post(ASK_PATH, json={"question": "テスト質問です"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "DeepSeek generation failed. Please try again later."
    }


def test_ask_ai_saves_question_as_unreviewed_ai_generated(client, monkeypatch, db):
    monkeypatch.setattr(
        deepseek_service,
        "chat_completion",
        lambda system_prompt, user_prompt: "回答内容",
    )

    response = client.post(ASK_PATH, json={"question": "AI保存テスト質問"})

    assert response.status_code == 200

    saved = (
        db.query(Question)
        .filter(Question.question == "AI保存テスト質問")
        .first()
    )

    assert saved is not None
    assert saved.answer == "回答内容"
    assert saved.status == "UNREVIEWED"
    assert saved.source == "AI_GENERATED"
    assert saved.language == "ja"
    assert saved.retrieved_question_ids == []


def test_ask_ai_save_failure_does_not_affect_response(client, monkeypatch, db):
    def _raise_embedding_error(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(
        deepseek_service, "chat_completion", lambda system_prompt, user_prompt: "回答"
    )
    monkeypatch.setattr(
        embedding_service, "create_embeddings", _raise_embedding_error
    )

    response = client.post(ASK_PATH, json={"question": "保存失敗テスト"})

    assert response.status_code == 200
    assert response.json() == {"answer": "回答"}

    saved = (
        db.query(Question)
        .filter(Question.question == "保存失敗テスト")
        .first()
    )

    assert saved is None


def test_ask_ai_rag_mode_calls_rag_service_and_saves_as_rag_result(
    client, monkeypatch, db
):
    monkeypatch.setattr(
        rag_service,
        "generate_rag_answer",
        lambda db, question: ("RAG回答", [11, 22]),
    )

    response = client.post(
        ASK_PATH, json={"question": "RAGモード質問", "mode": "RAG"}
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "RAG回答"}

    saved = (
        db.query(Question)
        .filter(Question.question == "RAGモード質問")
        .first()
    )

    assert saved is not None
    assert saved.answer == "RAG回答"
    assert saved.status == "UNREVIEWED"
    assert saved.source == "RAG_RESULT"
    assert saved.retrieved_question_ids == [11, 22]


def test_ask_ai_default_mode_does_not_call_rag_service(client, monkeypatch):
    def _fail(db, question):
        raise AssertionError("generate_rag_answer should not be called")

    monkeypatch.setattr(rag_service, "generate_rag_answer", _fail)
    monkeypatch.setattr(
        deepseek_service, "chat_completion", lambda system_prompt, user_prompt: "回答"
    )

    response = client.post(ASK_PATH, json={"question": "通常モード質問"})

    assert response.status_code == 200
    assert response.json() == {"answer": "回答"}


def test_ask_ai_invalid_mode_rejected(client):
    response = client.post(
        ASK_PATH, json={"question": "質問", "mode": "INVALID"}
    )

    assert response.status_code == 422


def test_ask_ai_question_too_short_rejected(client):
    response = client.post(ASK_PATH, json={"question": "1234"})

    assert response.status_code == 422


def test_ask_ai_question_too_long_rejected(client):
    response = client.post(ASK_PATH, json={"question": "あ" * 201})

    assert response.status_code == 422


def test_ask_ai_question_at_length_boundaries_accepted(client, monkeypatch):
    monkeypatch.setattr(
        deepseek_service, "chat_completion", lambda system_prompt, user_prompt: "回答"
    )

    short_response = client.post(ASK_PATH, json={"question": "12345"})
    long_response = client.post(ASK_PATH, json={"question": "あ" * 200})

    assert short_response.status_code == 200
    assert long_response.status_code == 200


def test_ask_ai_passes_max_tokens_to_deepseek(client, monkeypatch):
    from physics_ai_tutor.core.config import settings

    captured = {}

    class _FakeMessage:
        content = "回答"

    class _FakeChoice:
        message = _FakeMessage()

    class _FakeResponse:
        choices = [_FakeChoice()]

    def _fake_create(**kwargs):
        captured.update(kwargs)
        return _FakeResponse()

    monkeypatch.setattr(
        "physics_ai_tutor.services.deepseek_service.client.chat.completions.create",
        _fake_create,
    )

    response = client.post(ASK_PATH, json={"question": "テスト質問です"})

    assert response.status_code == 200
    assert captured["max_tokens"] == settings.deepseek_max_tokens


def test_ask_ai_rate_limit_exceeded_returns_429(client, monkeypatch):
    monkeypatch.setattr(
        deepseek_service, "chat_completion", lambda system_prompt, user_prompt: "回答"
    )

    for _ in range(10):
        ok_response = client.post(ASK_PATH, json={"question": "テスト質問です"})
        assert ok_response.status_code == 200

    limited_response = client.post(ASK_PATH, json={"question": "テスト質問です"})

    assert limited_response.status_code == 429


def test_ask_ai_admin_bypasses_minute_limit(client, admin_client, monkeypatch):
    monkeypatch.setattr(
        deepseek_service, "chat_completion", lambda system_prompt, user_prompt: "回答"
    )

    for _ in range(10):
        client.post(ASK_PATH, json={"question": "テスト質問です"})

    admin_response = admin_client.post(ASK_PATH, json={"question": "テスト質問です"})

    assert admin_response.status_code == 200
