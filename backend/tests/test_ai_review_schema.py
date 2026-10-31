from physics_ai_tutor.repositories import ai_review_repository
from physics_ai_tutor.schemas.ai_review import AiReviewCreate, AiReviewVerdict
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question_review import QuestionReviewReason
from physics_ai_tutor.services import deepseek_service
from tests.conftest import fake_generation

ASK_PATH = "/api/v1/ai/ask"


def _make_question(client, monkeypatch, text="AIレビューの対象質問") -> int:
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))
    return client.post(ASK_PATH, json={"question": text}).json()["question_id"]


def _review(question_id: int, **overrides) -> AiReviewCreate:
    defaults = dict(
        question_id=question_id,
        language=Language.JA,
        verdict=AiReviewVerdict.REJECT,
        confidence=0.9,
        reasons=[QuestionReviewReason.OFF_TOPIC],
        rationale="物理の質問ではない",
        rubric={"scope": 0, "physics": 2},
        model="deepseek-chat",
        prompt_version="r1",
    )
    defaults.update(overrides)
    return AiReviewCreate(**defaults)


def test_create_and_read_back_ai_review(client, db, monkeypatch):
    question_id = _make_question(client, monkeypatch)

    row = ai_review_repository.create(db, _review(question_id))
    db.commit()

    loaded = ai_review_repository.get_latest_for_question(db, question_id)

    assert loaded is not None
    assert loaded.id == row.id
    assert loaded.verdict == "REJECT"
    assert loaded.confidence == 0.9
    assert loaded.reasons == ["OFF_TOPIC"]
    assert loaded.rubric == {"scope": 0, "physics": 2}
    assert loaded.created_at is not None


def test_latest_review_wins_over_earlier_ones(client, db, monkeypatch):
    question_id = _make_question(client, monkeypatch)

    ai_review_repository.create(db, _review(question_id))
    second = ai_review_repository.create(
        db, _review(question_id, verdict=AiReviewVerdict.APPROVE, reasons=[])
    )
    db.commit()

    latest = ai_review_repository.get_latest_for_question(db, question_id)
    history = ai_review_repository.list_for_question(db, question_id)

    assert latest is not None and latest.id == second.id
    assert latest.verdict == "APPROVE"
    assert len(history) == 2


def test_unparseable_output_row_keeps_raw_text(client, db, monkeypatch):
    question_id = _make_question(client, monkeypatch)

    ai_review_repository.create(
        db,
        _review(
            question_id,
            verdict=None,
            confidence=None,
            reasons=[],
            rubric=None,
            rationale="raw model output that failed to parse",
        ),
    )
    db.commit()

    loaded = ai_review_repository.get_latest_for_question(db, question_id)

    assert loaded is not None
    assert loaded.verdict is None
    assert "failed to parse" in (loaded.rationale or "")


def test_deleting_the_question_cascades_to_ai_reviews(
    client, admin_client, db, monkeypatch
):
    question_id = _make_question(client, monkeypatch)
    ai_review_repository.create(db, _review(question_id))
    db.commit()

    assert admin_client.delete(f"/api/v1/questions/{question_id}").status_code == 204

    assert ai_review_repository.list_for_question(db, question_id) == []


def test_human_reviews_read_back_as_reviewer_kind_human(
    client, admin_client, monkeypatch
):
    question_id = _make_question(client, monkeypatch)

    admin_client.post(
        f"/api/v1/questions/{question_id}/review", json={"action": "APPROVE"}
    )

    history = admin_client.get(f"/api/v1/questions/{question_id}/reviews").json()

    assert history[0]["reviewer_kind"] == "human"
    assert history[0]["policy_name"] is None
