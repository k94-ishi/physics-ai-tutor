from physics_ai_tutor.core.exceptions import DeepSeekGenerationError
from physics_ai_tutor.services import deepseek_service

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

    response = client.post(ASK_PATH, json={"question": "質問"})

    assert response.status_code == 200


def test_ask_ai_failure_returns_503(client, monkeypatch):
    def _raise(system_prompt, user_prompt):
        raise DeepSeekGenerationError("boom")

    monkeypatch.setattr(deepseek_service, "chat_completion", _raise)

    response = client.post(ASK_PATH, json={"question": "質問"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "DeepSeek generation failed. Please try again later."
    }
