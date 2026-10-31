from physics_ai_tutor.repositories import ai_review_repository
from physics_ai_tutor.schemas.ai_review import AiReviewCreate, AiReviewVerdict
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question_review import QuestionReviewReason
from physics_ai_tutor.services import deepseek_service
from tests.conftest import fake_generation

ASK_PATH = "/api/v1/ai/ask"
QUESTIONS = "/api/v1/questions"


def _ask(client, monkeypatch, text, answer="回答"):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation(answer))
    return client.post(ASK_PATH, json={"question": text}).json()["question_id"]


def _store_review(db, question_id, verdict, confidence, reasons=(), suggested=None):
    ai_review_repository.create(
        db,
        AiReviewCreate(
            question_id=question_id,
            language=Language.JA,
            verdict=verdict,
            confidence=confidence,
            reasons=[QuestionReviewReason(code) for code in reasons],
            rationale="理由",
            suggested_answer=suggested,
            model="mock",
            prompt_version="r1",
        ),
    )
    db.commit()


def _seed(client, db, monkeypatch):
    """Three AI questions: high-confidence reject, low-confidence edit, no review."""
    reject = _ask(client, monkeypatch, "AI却下候補の質問です")
    edit = _ask(client, monkeypatch, "AI修正候補の質問です")
    none = _ask(client, monkeypatch, "AI未判定の質問です")
    _store_review(db, reject, AiReviewVerdict.REJECT, 0.95, ["OFF_TOPIC"])
    _store_review(db, edit, AiReviewVerdict.EDIT, 0.4, ["INCOMPLETE"], "修正案")
    return reject, edit, none


def _ids(response):
    return [item["id"] for item in response.json()["items"]]


def test_admin_list_includes_latest_ai_review(client, admin_client, db, monkeypatch):
    reject, _, none = _seed(client, db, monkeypatch)

    items = {item["id"]: item for item in admin_client.get(QUESTIONS).json()["items"]}

    assert items[reject]["ai_review"]["verdict"] == "REJECT"
    assert items[reject]["ai_review"]["confidence"] == 0.95
    assert items[reject]["ai_review"]["reasons"] == ["OFF_TOPIC"]
    assert items[none]["ai_review"] is None


def test_latest_review_wins_in_the_list(client, admin_client, db, monkeypatch):
    question_id = _ask(client, monkeypatch, "二回判定された質問です")
    _store_review(db, question_id, AiReviewVerdict.REJECT, 0.9)
    _store_review(db, question_id, AiReviewVerdict.APPROVE, 0.7)

    items = {item["id"]: item for item in admin_client.get(QUESTIONS).json()["items"]}

    assert items[question_id]["ai_review"]["verdict"] == "APPROVE"


def test_sort_by_ai_confidence_puts_unreviewed_last(
    client, admin_client, db, monkeypatch
):
    reject, edit, none = _seed(client, db, monkeypatch)

    response = admin_client.get(QUESTIONS, params={"sort": "ai_confidence"})

    assert _ids(response) == [reject, edit, none]


def test_filter_by_ai_verdict(client, admin_client, db, monkeypatch):
    reject, edit, none = _seed(client, db, monkeypatch)

    rejects = admin_client.get(QUESTIONS, params={"ai_verdict": "REJECT"})
    edits = admin_client.get(QUESTIONS, params={"ai_verdict": "EDIT"})
    unjudged = admin_client.get(QUESTIONS, params={"ai_verdict": "NONE"})

    assert _ids(rejects) == [reject]
    assert rejects.json()["total"] == 1
    assert _ids(edits) == [edit]
    assert _ids(unjudged) == [none]
    assert unjudged.json()["total"] == 1


def test_sort_by_asked_count(client, user_client, admin_client, db, monkeypatch):
    popular = _ask(client, monkeypatch, "よく聞かれる質問です")
    quiet = _ask(client, monkeypatch, "あまり聞かれない質問です")
    # Two signed-in asks (one hit) for the popular question, none for the other.
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))
    user_client.post(ASK_PATH, json={"question": "よく聞かれる質問です"})
    user_client.post(ASK_PATH, json={"question": "よく聞かれる質問です"})

    response = admin_client.get(QUESTIONS, params={"sort": "asked_count"})

    assert _ids(response)[:2] == [popular, quiet]


def test_sort_oldest_orders_by_creation(client, admin_client, db, monkeypatch):
    first = _ask(client, monkeypatch, "最初に作られた質問です")
    second = _ask(client, monkeypatch, "次に作られた質問です")

    response = admin_client.get(QUESTIONS, params={"sort": "oldest"})

    assert _ids(response) == [first, second]


def test_unknown_sort_or_verdict_is_rejected(admin_client):
    assert admin_client.get(QUESTIONS, params={"sort": "random"}).status_code == 422
    assert (
        admin_client.get(QUESTIONS, params={"ai_verdict": "MAYBE"}).status_code == 422
    )


def test_public_callers_get_no_ai_review_and_no_filtering(
    client, admin_client, db, monkeypatch
):
    reject, edit, _ = _seed(client, db, monkeypatch)
    # Publish both so a student can see them.
    for question_id in (reject, edit):
        admin_client.post(
            f"{QUESTIONS}/{question_id}/review", json={"action": "APPROVE"}
        )

    listed = client.get(QUESTIONS, params={"ai_verdict": "REJECT"}).json()
    detail = client.get(f"{QUESTIONS}/{reject}").json()

    # The filter is ignored for non-admins and the field stays null.
    assert {item["id"] for item in listed["items"]} >= {reject, edit}
    assert all(item["ai_review"] is None for item in listed["items"])
    assert detail["ai_review"] is None


def test_admin_detail_includes_suggested_answer(client, admin_client, db, monkeypatch):
    _, edit, _ = _seed(client, db, monkeypatch)

    detail = admin_client.get(f"{QUESTIONS}/{edit}").json()

    assert detail["ai_review"]["suggested_answer"] == "修正案"
    assert detail["ai_review"]["reasons"] == ["INCOMPLETE"]


def test_applying_the_suggestion_records_the_original_as_before(
    client, admin_client, db, monkeypatch
):
    question_id = _ask(
        client, monkeypatch, "提案を適用する質問です", answer="元のAI回答"
    )
    _store_review(
        db, question_id, AiReviewVerdict.EDIT, 0.8, ["INCOMPLETE"], "AIの修正案"
    )

    # What the edit page sends after "Apply suggested answer" + approve.
    review = admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={
            "action": "EDIT_APPROVE",
            "language": "ja",
            "question": "提案を適用する質問です",
            "answer": "AIの修正案",
            "reason": "INCOMPLETE",
        },
    )
    assert review.status_code == 200

    history = admin_client.get(f"{QUESTIONS}/{question_id}/reviews").json()[0]
    assert history["before_answer"] == "元のAI回答"
    assert history["after_answer"] == "AIの修正案"
    assert history["reviewer_kind"] == "human"
