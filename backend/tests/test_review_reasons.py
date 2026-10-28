from physics_ai_tutor.services import deepseek_service
from tests.conftest import fake_generation

ASK_PATH = "/api/v1/ai/ask"
QUESTIONS = "/api/v1/questions"


def _make_unreviewed(client, monkeypatch, text="理由コードのテスト質問"):
    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        fake_generation("回答"),
    )
    response = client.post(ASK_PATH, json={"question": text})
    return response.json()["question_id"]


def test_reject_without_reason_is_rejected(client, admin_client, monkeypatch):
    question_id = _make_unreviewed(client, monkeypatch)

    response = admin_client.post(
        f"{QUESTIONS}/{question_id}/review", json={"action": "REJECT"}
    )

    assert response.status_code == 422


def test_edit_approve_without_reason_is_rejected(client, admin_client, monkeypatch):
    question_id = _make_unreviewed(client, monkeypatch)

    response = admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={
            "action": "EDIT_APPROVE",
            "question": "編集後の質問",
            "answer": "編集後の回答",
        },
    )

    assert response.status_code == 422


def test_other_reason_requires_comment(client, admin_client, monkeypatch):
    question_id = _make_unreviewed(client, monkeypatch)

    bare = admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={"action": "REJECT", "reason": "OTHER"},
    )
    blank = admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={"action": "REJECT", "reason": "OTHER", "comment": "  "},
    )
    explained = admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={"action": "REJECT", "reason": "OTHER", "comment": "別の理由"},
    )

    assert bare.status_code == 422
    assert blank.status_code == 422
    assert explained.status_code == 200


def test_unknown_reason_is_rejected(client, admin_client, monkeypatch):
    question_id = _make_unreviewed(client, monkeypatch)

    response = admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={"action": "REJECT", "reason": "NOT_A_CODE"},
    )

    assert response.status_code == 422


def test_approve_needs_no_reason(client, admin_client, monkeypatch):
    question_id = _make_unreviewed(client, monkeypatch)

    response = admin_client.post(
        f"{QUESTIONS}/{question_id}/review", json={"action": "APPROVE"}
    )

    assert response.status_code == 200


def test_reason_appears_in_review_history(client, admin_client, monkeypatch):
    question_id = _make_unreviewed(client, monkeypatch)

    admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={"action": "REJECT", "reason": "TOO_ADVANCED", "comment": "微積分を使用"},
    )

    history = admin_client.get(f"{QUESTIONS}/{question_id}/reviews").json()

    assert history[0]["reason"] == "TOO_ADVANCED"
    assert history[0]["comment"] == "微積分を使用"


def test_bulk_reject_requires_and_applies_one_reason(client, admin_client, monkeypatch):
    first = _make_unreviewed(client, monkeypatch, "一括理由テスト質問1")
    second = _make_unreviewed(client, monkeypatch, "一括理由テスト質問2")

    missing = admin_client.post(
        f"{QUESTIONS}/bulk-review",
        json={"question_ids": [first, second], "action": "REJECT"},
    )
    assert missing.status_code == 422

    applied = admin_client.post(
        f"{QUESTIONS}/bulk-review",
        json={
            "question_ids": [first, second],
            "action": "REJECT",
            "reason": "OFF_TOPIC",
        },
    )
    assert applied.status_code == 200

    for question_id in (first, second):
        history = admin_client.get(f"{QUESTIONS}/{question_id}/reviews").json()
        assert history[0]["reason"] == "OFF_TOPIC"


def test_bulk_approve_needs_no_reason(client, admin_client, monkeypatch):
    question_id = _make_unreviewed(client, monkeypatch, "一括承認テスト質問")

    response = admin_client.post(
        f"{QUESTIONS}/bulk-review",
        json={"question_ids": [question_id], "action": "APPROVE"},
    )

    assert response.status_code == 200
