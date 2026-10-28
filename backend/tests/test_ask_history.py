from physics_ai_tutor.models import QuestionAsk, User
from physics_ai_tutor.services import deepseek_service
from tests.conftest import fake_generation

ASK_PATH = "/api/v1/ai/ask"
MY_QUESTIONS_PATH = "/api/v1/users/me/questions"

MY_QUESTIONS_PATH = "/api/v1/users/me/questions"
REJECT_BODY = {"action": "REJECT", "reason": "PHYSICS_ERROR"}


def _mock_answer(monkeypatch, answer="回答"):
    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        fake_generation(answer),
    )


def test_miss_and_cache_hit_both_record_an_ask(user_client, db, monkeypatch):
    _mock_answer(monkeypatch)

    first = user_client.post(ASK_PATH, json={"question": "履歴テスト質問です"})
    second = user_client.post(ASK_PATH, json={"question": "履歴テスト質問です"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["cached"] is True

    user = db.query(User).filter_by(email="user@example.com").one()
    asks = db.query(QuestionAsk).filter_by(user_id=user.id).all()

    assert len(asks) == 2
    assert {ask.question_id for ask in asks} == {first.json()["question_id"]}


def test_anonymous_ask_creates_no_rows(client, db, monkeypatch):
    _mock_answer(monkeypatch)

    assert (
        client.post(ASK_PATH, json={"question": "匿名の履歴テスト"}).status_code == 200
    )

    assert db.query(QuestionAsk).count() == 0


def test_my_questions_lists_own_asks_newest_first(user_client, monkeypatch):
    _mock_answer(monkeypatch)

    user_client.post(ASK_PATH, json={"question": "一つ目の質問です"})
    user_client.post(ASK_PATH, json={"question": "二つ目の質問です"})

    response = user_client.get(MY_QUESTIONS_PATH)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["question"] for item in body["items"]] == [
        "二つ目の質問です",
        "一つ目の質問です",
    ]
    assert body["items"][0]["status"] == "UNREVIEWED"
    assert body["items"][0]["answer"] == "回答"
    assert body["items"][0]["language"] == "ja"


def test_my_questions_does_not_show_other_users_asks(
    user_client, admin_client, monkeypatch
):
    _mock_answer(monkeypatch)

    admin_client.post(ASK_PATH, json={"question": "管理者の履歴質問"})

    response = user_client.get(MY_QUESTIONS_PATH)

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_my_questions_requires_authentication(client):
    assert client.get(MY_QUESTIONS_PATH).status_code == 401


def test_my_questions_shows_teacher_correction_after_edit_approve(
    user_client, admin_client, monkeypatch
):
    _mock_answer(monkeypatch)

    asked = user_client.post(ASK_PATH, json={"question": "添削される質問です"})
    question_id = asked.json()["question_id"]

    review = admin_client.post(
        f"/api/v1/questions/{question_id}/review",
        json={
            "action": "EDIT_APPROVE",
            "reason": "INCOMPLETE",
            "language": "ja",
            "question": "添削される質問です",
            "answer": "先生が修正した回答",
        },
    )
    assert review.status_code == 200

    item = user_client.get(MY_QUESTIONS_PATH).json()["items"][0]

    assert item["status"] == "APPROVED"
    assert item["answer"] == "先生が修正した回答"


def test_my_questions_withholds_rejected_answer(user_client, admin_client, monkeypatch):
    _mock_answer(monkeypatch, answer="却下される回答")

    asked = user_client.post(ASK_PATH, json={"question": "却下される質問です"})
    question_id = asked.json()["question_id"]

    admin_client.post(f"/api/v1/questions/{question_id}/review", json=REJECT_BODY)

    item = user_client.get(MY_QUESTIONS_PATH).json()["items"][0]

    assert item["status"] == "REJECTED"
    assert item["question"] == "却下される質問です"
    assert item["answer"] is None


def test_my_questions_paginates(user_client, monkeypatch):
    _mock_answer(monkeypatch)

    for index in range(3):
        user_client.post(ASK_PATH, json={"question": f"ページングの質問その{index}"})

    page = user_client.get(MY_QUESTIONS_PATH, params={"page": 2, "size": 2}).json()

    assert page["total"] == 3
    assert len(page["items"]) == 1
    assert page["items"][0]["question"] == "ページングの質問その0"


def test_account_deletion_unlinks_asks(user_client, db, monkeypatch):
    _mock_answer(monkeypatch)

    user_client.post(ASK_PATH, json={"question": "削除前の質問です"})

    assert user_client.delete("/api/v1/users/me").status_code == 204

    ask = db.query(QuestionAsk).one()
    db.refresh(ask)
    assert ask.user_id is None
