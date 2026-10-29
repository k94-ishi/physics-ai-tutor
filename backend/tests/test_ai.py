from physics_ai_tutor.core.exceptions import (
    DeepSeekGenerationError,
    EmbeddingGenerationError,
)
from physics_ai_tutor.models import Question
from physics_ai_tutor.services import deepseek_service, embedding_service, rag_service
from tests.conftest import fake_generation

ASK_PATH = "/api/v1/ai/ask"


def test_ask_ai_returns_answer(client, monkeypatch):
    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        fake_generation("加速度は単位時間あたりの速度の変化量です。"),
    )

    response = client.post(ASK_PATH, json={"question": "加速度って何？"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "加速度は単位時間あたりの速度の変化量です。"
    assert body["language"] == "ja"
    assert body["cached"] is False
    assert body["status"] == "UNREVIEWED"


def test_ask_ai_empty_question_rejected(client):
    response = client.post(ASK_PATH, json={"question": ""})

    assert response.status_code == 422


def test_ask_ai_does_not_require_authentication(client, monkeypatch):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    response = client.post(ASK_PATH, json={"question": "テスト質問です"})

    assert response.status_code == 200


def test_ask_ai_failure_returns_503(client, monkeypatch):
    def _raise(system_prompt, user_prompt):
        raise DeepSeekGenerationError("boom")

    monkeypatch.setattr(deepseek_service, "generate_answer", _raise)

    response = client.post(ASK_PATH, json={"question": "テスト質問です"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "DeepSeek generation failed. Please try again later."
    }


def test_ask_ai_saves_question_as_unreviewed_ai_generated(client, monkeypatch, db):
    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        fake_generation("回答内容"),
    )

    response = client.post(ASK_PATH, json={"question": "AI保存テスト質問"})

    assert response.status_code == 200

    saved = (
        db.query(Question).filter(Question.question_ja == "AI保存テスト質問").first()
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

    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))
    monkeypatch.setattr(embedding_service, "create_embeddings", _raise_embedding_error)

    response = client.post(ASK_PATH, json={"question": "保存失敗テスト"})

    assert response.status_code == 200
    assert response.json()["answer"] == "回答"
    assert response.json()["question_id"] is None

    saved = db.query(Question).filter(Question.question_ja == "保存失敗テスト").first()

    assert saved is None


def test_ask_ai_rag_mode_calls_rag_service_and_saves_as_rag_result(
    client, monkeypatch, db
):
    monkeypatch.setattr(
        rag_service,
        "generate_rag_answer",
        lambda db, question, retrieved_question_ids=None, language="ja": (
            fake_generation("RAG回答")(None, None),
            [11, 22],
        ),
    )

    response = client.post(ASK_PATH, json={"question": "RAGモード質問", "mode": "RAG"})

    assert response.status_code == 200
    assert response.json()["answer"] == "RAG回答"

    saved = db.query(Question).filter(Question.question_ja == "RAGモード質問").first()

    assert saved is not None
    assert saved.answer == "RAG回答"
    assert saved.status == "UNREVIEWED"
    assert saved.source == "RAG_RESULT"
    assert saved.retrieved_question_ids == [11, 22]


def test_ask_ai_default_mode_does_not_call_rag_service(client, monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("generate_rag_answer should not be called")

    monkeypatch.setattr(rag_service, "generate_rag_answer", _fail)
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    response = client.post(ASK_PATH, json={"question": "通常モード質問"})

    assert response.status_code == 200
    assert response.json()["answer"] == "回答"


def test_ask_ai_invalid_mode_rejected(client):
    response = client.post(ASK_PATH, json={"question": "質問", "mode": "INVALID"})

    assert response.status_code == 422


def test_ask_ai_question_too_short_rejected(client):
    response = client.post(ASK_PATH, json={"question": "1234"})

    assert response.status_code == 422


def test_ask_ai_question_too_long_rejected(client):
    response = client.post(ASK_PATH, json={"question": "あ" * 201})

    assert response.status_code == 422


def test_ask_ai_question_at_length_boundaries_accepted(client, monkeypatch):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

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
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    # Distinct questions so every request is a cache miss that costs quota.
    for index in range(3):
        ok_response = client.post(ASK_PATH, json={"question": f"テスト質問その{index}"})
        assert ok_response.status_code == 200

    limited_response = client.post(ASK_PATH, json={"question": "テスト質問その3"})

    assert limited_response.status_code == 429


def test_ask_ai_rag_mode_passes_retrieved_question_ids_to_service(client, monkeypatch):
    captured = {}

    def _fake_generate_rag_answer(
        db, question, retrieved_question_ids=None, language="ja"
    ):
        captured["retrieved_question_ids"] = retrieved_question_ids
        return fake_generation("RAG回答")(None, None), retrieved_question_ids or []

    monkeypatch.setattr(rag_service, "generate_rag_answer", _fake_generate_rag_answer)

    response = client.post(
        ASK_PATH,
        json={
            "question": "テスト質問です",
            "mode": "RAG",
            "retrieved_question_ids": [3, 7],
        },
    )

    assert response.status_code == 200
    assert captured["retrieved_question_ids"] == [3, 7]


def test_ask_ai_cache_hit_does_not_consume_quota(client, monkeypatch):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    first = client.post(ASK_PATH, json={"question": "キャッシュされる質問"})
    assert first.status_code == 200
    assert first.json()["cached"] is False

    # Identical questions are served from cache and stay free.
    for _ in range(5):
        hit = client.post(ASK_PATH, json={"question": "キャッシュされる質問"})
        assert hit.status_code == 200
        assert hit.json()["cached"] is True

    # The five cache hits left the remaining generation quota untouched.
    second = client.post(ASK_PATH, json={"question": "新しい質問その2"})
    third = client.post(ASK_PATH, json={"question": "新しい質問その3"})
    limited = client.post(ASK_PATH, json={"question": "新しい質問その4"})

    assert second.status_code == 200
    assert third.status_code == 200
    assert limited.status_code == 429


def _exhaust_anonymous_quota(client):
    # Distinct questions so each request is a generation, not a cache hit.
    for index in range(3):
        response = client.post(ASK_PATH, json={"question": f"匿名の質問その{index}"})
        assert response.status_code == 200

    limited = client.post(ASK_PATH, json={"question": "匿名の質問その3"})
    assert limited.status_code == 429


def test_ask_ai_admin_not_limited_by_anonymous_bucket(
    client, admin_client, monkeypatch
):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    _exhaust_anonymous_quota(client)

    admin_response = admin_client.post(ASK_PATH, json={"question": "管理者の質問です"})

    assert admin_response.status_code == 200


def test_ask_ai_signed_in_user_not_limited_by_anonymous_bucket(
    client, user_client, monkeypatch
):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    _exhaust_anonymous_quota(client)

    # The signed-in user is counted per account, not per IP.
    user_response = user_client.post(ASK_PATH, json={"question": "会員の質問です"})

    assert user_response.status_code == 200


def test_ask_ai_signed_in_user_limited_to_ten_per_hour(user_client, monkeypatch):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    for index in range(10):
        payload = {"question": f"会員の質問その{index}"}
        assert user_client.post(ASK_PATH, json=payload).status_code == 200

    limited = user_client.post(ASK_PATH, json={"question": "会員の質問その10"})

    assert limited.status_code == 429


def test_ask_ai_stores_generation_metadata(client, monkeypatch, db):
    from physics_ai_tutor.core import prompts

    monkeypatch.setattr(
        deepseek_service, "generate_answer", fake_generation("メタデータ回答")
    )

    response = client.post(ASK_PATH, json={"question": "メタデータの質問です"})
    assert response.status_code == 200

    saved = db.query(Question).filter_by(id=response.json()["question_id"]).one()

    assert saved.generation_model == "mock-model"
    assert saved.prompt_version == prompts.ANSWER_PROMPT_VERSION
    assert saved.generation_mode == "DIRECT"
    assert saved.prompt_tokens == 11
    assert saved.completion_tokens == 22


def test_ask_ai_rag_mode_stores_rag_generation_mode(client, monkeypatch, db):
    monkeypatch.setattr(
        rag_service,
        "generate_rag_answer",
        lambda db, question, retrieved_question_ids=None, language="ja": (
            fake_generation("RAG回答")(None, None),
            [],
        ),
    )

    response = client.post(
        ASK_PATH, json={"question": "RAGメタデータの質問", "mode": "RAG"}
    )

    saved = db.query(Question).filter_by(id=response.json()["question_id"]).one()

    assert saved.generation_mode == "RAG"
    assert saved.generation_model == "mock-model"


def test_generation_metadata_admin_only_in_responses(
    client, admin_client, monkeypatch, db
):
    monkeypatch.setattr(
        deepseek_service, "generate_answer", fake_generation("公開範囲の回答")
    )

    asked = client.post(ASK_PATH, json={"question": "公開範囲テスト質問"})
    question_id = asked.json()["question_id"]
    admin_client.post(
        f"/api/v1/questions/{question_id}/review", json={"action": "APPROVE"}
    )

    public = client.get(f"/api/v1/questions/{question_id}").json()
    admin = admin_client.get(f"/api/v1/questions/{question_id}").json()

    assert public["generation"] is None
    assert admin["generation"]["model"] == "mock-model"
    assert admin["generation"]["mode"] == "DIRECT"


def test_manual_question_has_no_generation_metadata(admin_client, db):
    created = admin_client.post(
        "/api/v1/questions",
        json={"question": "手動登録の質問", "answer": "手動の回答"},
    )
    question_id = created.json()["id"]

    saved = db.query(Question).filter_by(id=question_id).one()
    assert saved.generation_model is None
    assert saved.prompt_version is None

    admin = admin_client.get(f"/api/v1/questions/{question_id}").json()
    assert admin["generation"]["model"] is None


def test_ask_ai_off_topic_reply_is_returned_but_never_saved(client, monkeypatch, db):
    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        fake_generation(
            "[OFF_TOPIC] ごめんなさい、この質問には答えられません。"
            "高校物理について質問してください。"
        ),
    )

    response = client.post(ASK_PATH, json={"question": "英語の宿題を手伝って"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith("ごめんなさい")
    assert "[OFF_TOPIC]" not in body["answer"]
    assert body["question_id"] is None
    assert body["status"] is None

    assert db.query(Question).count() == 0


def test_ask_ai_off_topic_with_bare_sentinel_uses_fallback(client, monkeypatch):
    monkeypatch.setattr(
        deepseek_service, "generate_answer", fake_generation("[OFF_TOPIC]")
    )

    response = client.post(ASK_PATH, json={"question": "こんにちは、元気ですか"})

    assert response.status_code == 200
    assert "高校物理" in response.json()["answer"]


def test_ask_ai_off_topic_records_no_ask_history(user_client, db, monkeypatch):
    from physics_ai_tutor.models import QuestionAsk

    monkeypatch.setattr(
        deepseek_service, "generate_answer", fake_generation("[OFF_TOPIC] 回答不可")
    )

    assert (
        user_client.post(ASK_PATH, json={"question": "数学の宿題を解いて"}).status_code
        == 200
    )

    assert db.query(QuestionAsk).count() == 0


def test_ask_ai_off_topic_still_consumes_quota(client, monkeypatch):
    monkeypatch.setattr(
        deepseek_service, "generate_answer", fake_generation("[OFF_TOPIC] 回答不可")
    )

    # Anonymous limit is 3/hour; off-topic asks must not be free retries.
    for index in range(3):
        ok = client.post(ASK_PATH, json={"question": f"雑談その{index}です"})
        assert ok.status_code == 200

    limited = client.post(ASK_PATH, json={"question": "雑談その3です"})

    assert limited.status_code == 429
