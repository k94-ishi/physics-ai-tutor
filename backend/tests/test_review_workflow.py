"""End-to-end tests for the AI answer review workflow.

These exercise the full path a generated answer takes: saved as UNREVIEWED,
hidden from students, reviewed by an admin, then published or rejected.
"""

from physics_ai_tutor.models import QuestionEmbedding
from physics_ai_tutor.services import deepseek_service

QUESTIONS = "/api/v1/questions"
ASK = "/api/v1/ai/ask"


def _ask(client, monkeypatch, question: str, answer: str = "AIの回答") -> None:
    monkeypatch.setattr(
        deepseek_service, "chat_completion", lambda system, user: answer
    )
    assert client.post(ASK, json={"question": question}).status_code == 200


def _find_id_as_admin(admin_client, question: str) -> int:
    response = admin_client.get(QUESTIONS, params={"keyword": question})
    items = response.json()["items"]
    assert len(items) == 1
    return items[0]["id"]


def test_ai_answer_is_hidden_until_approved(client, admin_client, monkeypatch):
    _ask(client, monkeypatch, "AI生成の未公開質問ですか？")
    question_id = _find_id_as_admin(admin_client, "AI生成の未公開質問")

    assert client.get(f"{QUESTIONS}/{question_id}").status_code == 404
    assert client.get(QUESTIONS).json()["total"] == 0

    approve = admin_client.post(
        f"{QUESTIONS}/{question_id}/review", json={"action": "APPROVE"}
    )

    assert approve.status_code == 200
    assert approve.json()["status"] == "APPROVED"
    assert client.get(f"{QUESTIONS}/{question_id}").status_code == 200
    assert client.get(QUESTIONS).json()["total"] == 1


def test_rejected_answer_stays_hidden_and_is_filterable_by_admin(
    client, admin_client, monkeypatch
):
    _ask(client, monkeypatch, "却下されるAI質問ですか？")
    question_id = _find_id_as_admin(admin_client, "却下されるAI質問")

    reject = admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={"action": "REJECT", "comment": "内容が不正確"},
    )

    assert reject.status_code == 200
    assert client.get(f"{QUESTIONS}/{question_id}").status_code == 404

    rejected = admin_client.get(QUESTIONS, params={"status": "REJECTED"}).json()
    assert [item["id"] for item in rejected["items"]] == [question_id]

    history = admin_client.get(f"{QUESTIONS}/{question_id}/reviews").json()
    assert len(history) == 1
    assert history[0]["action"] == "REJECT"
    assert history[0]["comment"] == "内容が不正確"


def test_edit_approve_records_before_and_after_and_reembeds(
    client, admin_client, monkeypatch, db
):
    _ask(client, monkeypatch, "編集されるAI質問ですか？", answer="元の回答")
    question_id = _find_id_as_admin(admin_client, "編集されるAI質問")

    response = admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={
            "action": "EDIT_APPROVE",
            "question": "編集されるAI質問ですか？",
            "answer": "修正された回答",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["answer"] == "修正された回答"

    history = admin_client.get(f"{QUESTIONS}/{question_id}/reviews").json()
    assert history[0]["before_answer"] == "元の回答"
    assert history[0]["after_answer"] == "修正された回答"
    assert history[0]["reviewer_id"] is not None

    # One question and one answer embedding per language must remain.
    embeddings = (
        db.query(QuestionEmbedding)
        .filter(QuestionEmbedding.question_id == question_id)
        .all()
    )
    assert sorted((e.language, e.type) for e in embeddings) == [
        ("en", "answer"),
        ("en", "question"),
        ("ja", "answer"),
        ("ja", "question"),
    ]


def test_bulk_review_publishes_each_question_with_history(
    client, admin_client, monkeypatch
):
    _ask(client, monkeypatch, "一括承認される質問その一ですか？")
    _ask(client, monkeypatch, "一括承認される質問その二ですか？")
    first = _find_id_as_admin(admin_client, "一括承認される質問その一")
    second = _find_id_as_admin(admin_client, "一括承認される質問その二")

    response = admin_client.post(
        f"{QUESTIONS}/bulk-review",
        json={"question_ids": [first, second, 99999], "action": "APPROVE"},
    )

    assert response.status_code == 200
    assert response.json()["not_found_ids"] == [99999]
    assert client.get(QUESTIONS).json()["total"] == 2

    for question_id in (first, second):
        history = admin_client.get(f"{QUESTIONS}/{question_id}/reviews").json()
        assert [entry["action"] for entry in history] == ["APPROVE"]


def test_related_questions_hide_unreviewed_from_public(
    client, admin_client, monkeypatch
):
    source_id = admin_client.post(
        QUESTIONS, json={"question": "関連元の承認済み質問", "answer": "回答"}
    ).json()["id"]
    _ask(client, monkeypatch, "関連する未レビュー質問ですか？")
    unreviewed_id = _find_id_as_admin(admin_client, "関連する未レビュー質問")

    public_ids = {
        item["id"] for item in client.get(f"{QUESTIONS}/{source_id}/related").json()
    }
    admin_ids = {
        item["id"]
        for item in admin_client.get(f"{QUESTIONS}/{source_id}/related").json()
    }

    assert unreviewed_id not in public_ids
    assert unreviewed_id in admin_ids


def test_non_admin_user_cannot_review(user_client, admin_client, client, monkeypatch):
    _ask(client, monkeypatch, "一般ユーザーが触れない質問ですか？")
    question_id = _find_id_as_admin(admin_client, "一般ユーザーが触れない質問")

    response = user_client.post(
        f"{QUESTIONS}/{question_id}/review", json={"action": "APPROVE"}
    )

    assert response.status_code == 403
    assert client.get(f"{QUESTIONS}/{question_id}").status_code == 404
