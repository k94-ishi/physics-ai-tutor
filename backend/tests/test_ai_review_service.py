import json

import pytest
from sqlalchemy.orm import sessionmaker

from physics_ai_tutor.cli import review_pending as review_pending_cli
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.models import AiReview, Question
from physics_ai_tutor.services import ai_review_service, deepseek_service
from physics_ai_tutor.services.deepseek_service import GenerationResult
from tests.conftest import engine, fake_generation

ASK_PATH = "/api/v1/ai/ask"

VALID_REVIEW = {
    "verdict": "EDIT",
    "confidence": 0.8,
    "reasons": ["INCOMPLETE"],
    "rubric": {
        "physics": 2,
        "math": 2,
        "completeness": 1,
        "level": 2,
        "clarity": 1,
        "formatting": 2,
        "scope": 2,
    },
    "rationale": "説明が途中で終わっている。",
    "suggested_answer": "修正済みの回答",
}


@pytest.fixture
def review_enabled(monkeypatch):
    monkeypatch.setattr(settings, "ai_review_enabled", True)


def _sequenced_generation(monkeypatch, *contents):
    """generate_answer returns the given contents in order of the calls."""
    queue = list(contents)

    def _next(system_prompt, user_prompt):
        content = queue.pop(0)
        return GenerationResult(
            content=content, model="mock-model", prompt_tokens=5, completion_tokens=7
        )

    monkeypatch.setattr(deepseek_service, "generate_answer", _next)


def test_new_ai_answer_gets_exactly_one_review(client, db, monkeypatch, review_enabled):
    _sequenced_generation(monkeypatch, "生成された回答", json.dumps(VALID_REVIEW))

    response = client.post(ASK_PATH, json={"question": "レビューされる質問です"})
    assert response.status_code == 200

    reviews = db.query(AiReview).all()
    assert len(reviews) == 1
    review = reviews[0]

    assert review.verdict == "EDIT"
    assert review.confidence == 0.8
    assert review.reasons == ["INCOMPLETE"]
    assert review.rubric["completeness"] == 1
    assert review.suggested_answer == "修正済みの回答"
    assert review.model == "mock-model"
    assert review.prompt_version == ai_review_service.REVIEW_PROMPT_VERSION
    assert review.language == "ja"

    # Advisory only: the question's status is untouched.
    question = db.get(Question, response.json()["question_id"])
    assert question.status == "UNREVIEWED"


def test_cache_hit_triggers_no_review(client, db, monkeypatch, review_enabled):
    _sequenced_generation(monkeypatch, "回答", json.dumps(VALID_REVIEW))

    client.post(ASK_PATH, json={"question": "キャッシュとレビューの質問"})
    client.post(ASK_PATH, json={"question": "キャッシュとレビューの質問"})

    assert db.query(AiReview).count() == 1


def test_disabled_flag_skips_the_review(client, db, monkeypatch):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))

    client.post(ASK_PATH, json={"question": "フラグ無効の質問です"})

    assert db.query(AiReview).count() == 0


def test_malformed_output_is_stored_as_a_visible_failure(
    client, db, monkeypatch, review_enabled
):
    _sequenced_generation(monkeypatch, "回答", "I think this answer is fine!")

    response = client.post(ASK_PATH, json={"question": "壊れた出力の質問です"})
    assert response.status_code == 200

    review = db.query(AiReview).one()
    assert review.verdict is None
    assert "fine!" in review.rationale

    question = db.get(Question, response.json()["question_id"])
    assert question.status == "UNREVIEWED"


def test_reviewer_failure_does_not_break_translation(
    client, db, monkeypatch, review_enabled
):
    def _answer_then_error(system_prompt, user_prompt):
        if "審査します" in system_prompt or "screening" in system_prompt:
            raise RuntimeError("reviewer down")
        return fake_generation("回答")(system_prompt, user_prompt)

    monkeypatch.setattr(deepseek_service, "generate_answer", _answer_then_error)

    response = client.post(ASK_PATH, json={"question": "翻訳は守られる質問です"})
    assert response.status_code == 200

    question = db.get(Question, response.json()["question_id"])
    db.refresh(question)
    # The conftest fake translator ran despite the reviewer failure.
    assert question.question_en == "[en] 翻訳は守られる質問です"
    assert db.query(AiReview).count() == 0


def test_output_wrapped_in_code_fences_is_parsed(
    client, db, monkeypatch, review_enabled
):
    fenced = "```json\n" + json.dumps(VALID_REVIEW) + "\n```"
    _sequenced_generation(monkeypatch, "回答", fenced)

    client.post(ASK_PATH, json={"question": "フェンス付き出力の質問"})

    assert db.query(AiReview).one().verdict == "EDIT"


def test_unknown_codes_and_out_of_range_values_are_coerced(
    client, db, monkeypatch, review_enabled
):
    messy = dict(
        VALID_REVIEW,
        verdict="REJECT",
        confidence=1.7,
        reasons=["OFF_TOPIC", "NOT_A_CODE"],
        rubric={"physics": 9, "scope": 0, "unknown": 1},
    )
    _sequenced_generation(monkeypatch, "回答", json.dumps(messy))

    client.post(ASK_PATH, json={"question": "乱れた出力の質問です"})

    review = db.query(AiReview).one()
    assert review.verdict == "REJECT"
    assert review.confidence == 1.0
    assert review.reasons == ["OFF_TOPIC"]
    assert review.rubric == {"scope": 0}


def test_reviewer_prompt_matches_the_questions_language(
    client, db, monkeypatch, review_enabled
):
    captured = []

    def _capture(system_prompt, user_prompt):
        captured.append((system_prompt, user_prompt))
        content = json.dumps(VALID_REVIEW) if len(captured) % 2 == 0 else "An answer."
        return GenerationResult(
            content=content, model="mock-model", prompt_tokens=1, completion_tokens=1
        )

    monkeypatch.setattr(deepseek_service, "generate_answer", _capture)

    client.post(ASK_PATH, json={"question": "What is momentum here?", "language": "en"})

    reviewer_system, reviewer_user = captured[1]
    assert "screening" in reviewer_system
    assert "AI answer:" in reviewer_user
    assert "What is momentum here?" in reviewer_user

    review = db.query(AiReview).one()
    assert review.language == "en"


@pytest.fixture
def _bind_review_cli(monkeypatch, db):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(review_pending_cli, "SessionLocal", factory)


def test_cli_backfills_only_pending_questions(
    client, db, monkeypatch, _bind_review_cli
):
    # Two generations with the reviewer disabled -> no rows yet.
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))
    client.post(ASK_PATH, json={"question": "バックフィル質問その1"})
    client.post(ASK_PATH, json={"question": "バックフィル質問その2"})
    assert db.query(AiReview).count() == 0

    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        fake_generation(json.dumps(VALID_REVIEW)),
    )

    assert review_pending_cli.main(limit=1) == 1
    assert db.query(AiReview).count() == 1

    # The second run picks up the remaining question, not the reviewed one.
    assert review_pending_cli.main(limit=10) == 1
    assert db.query(AiReview).count() == 2
    assert review_pending_cli.main(limit=10) == 0


def test_service_skips_non_ai_and_already_reviewed_questions(
    admin_client, db, monkeypatch
):
    created = admin_client.post(
        "/api/v1/questions",
        json={"question": "手動の質問です", "answer": "手動の回答"},
    )
    question = db.get(Question, created.json()["id"])

    assert ai_review_service.review_question(db, question) is None
    assert db.query(AiReview).count() == 0
