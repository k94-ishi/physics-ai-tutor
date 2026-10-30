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


# --- runs ----------------------------------------------------------------------


def _three_pending(client, monkeypatch):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))
    return [
        client.post(ASK_PATH, json={"question": f"ラン対象の質問その{i}"}).json()[
            "question_id"
        ]
        for i in range(3)
    ]


def test_run_over_pending_questions_counts_and_sums_tokens(
    client, db, monkeypatch, _bind_review_cli
):
    ids = _three_pending(client, monkeypatch)
    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        fake_generation(json.dumps(VALID_REVIEW)),
    )

    from physics_ai_tutor.services import ai_review_service as service

    run = service.start_run(db, scope="pending", trigger="cli")
    assert run.requested_count == 3
    assert run.question_ids == ids

    finished = service.execute_run(db, run.id)

    assert finished.status == "done"
    assert finished.reviewed_count == 3
    assert finished.failed_count == 0
    # fake_generation reports 11/22 tokens per call.
    assert finished.prompt_tokens == 33
    assert finished.completion_tokens == 66
    assert finished.finished_at is not None
    assert db.query(AiReview).count() == 3


def test_second_run_refused_while_one_is_running(client, db, monkeypatch):
    _three_pending(client, monkeypatch)
    from physics_ai_tutor.services import ai_review_service as service

    service.start_run(db, scope="pending", trigger="cli")

    with pytest.raises(service.RunInProgressError):
        service.start_run(db, scope="pending", trigger="cli")

    from physics_ai_tutor.models import AiReviewRun

    assert db.query(AiReviewRun).count() == 1


def test_one_failure_is_counted_and_does_not_stop_the_run(client, db, monkeypatch):
    ids = _three_pending(client, monkeypatch)
    calls = {"n": 0}

    def _second_fails(system_prompt, user_prompt):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("reviewer down")
        return GenerationResult(
            content=json.dumps(VALID_REVIEW),
            model="mock-model",
            prompt_tokens=11,
            completion_tokens=22,
        )

    monkeypatch.setattr(deepseek_service, "generate_answer", _second_fails)
    from physics_ai_tutor.services import ai_review_service as service

    run = service.start_run(db, scope="pending", trigger="cli")
    finished = service.execute_run(db, run.id)

    assert finished.status == "done"
    assert finished.reviewed_count == 2
    assert finished.failed_count == 1
    assert sorted(r.question_id for r in db.query(AiReview)) == sorted([ids[0], ids[2]])


def test_stale_scope_picks_only_old_prompt_versions(client, db, monkeypatch):
    first, second, _ = _three_pending(client, monkeypatch)
    from physics_ai_tutor.repositories import ai_review_repository
    from physics_ai_tutor.schemas.ai_review import AiReviewCreate, AiReviewVerdict
    from physics_ai_tutor.schemas.language import Language
    from physics_ai_tutor.services import ai_review_service as service

    versions = ((first, "r0"), (second, service.REVIEW_PROMPT_VERSION))
    for question_id, version in versions:
        ai_review_repository.create(
            db,
            AiReviewCreate(
                question_id=question_id,
                language=Language.JA,
                verdict=AiReviewVerdict.APPROVE,
                model="mock",
                prompt_version=version,
            ),
        )
    db.commit()

    assert service.eligible_question_ids(db, "stale") == [first]


def test_daily_cap_truncates_and_then_refuses(client, db, monkeypatch):
    _three_pending(client, monkeypatch)
    monkeypatch.setattr(settings, "ai_review_daily_cap", 2)
    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        fake_generation(json.dumps(VALID_REVIEW)),
    )
    from physics_ai_tutor.services import ai_review_service as service

    run = service.start_run(db, scope="pending", trigger="cli")
    assert run.requested_count == 2
    service.execute_run(db, run.id)

    with pytest.raises(service.DailyCapExhaustedError):
        service.start_run(db, scope="pending", trigger="cli")


def test_selected_scope_keeps_only_reviewable_ids(
    client, admin_client, db, monkeypatch
):
    ids = _three_pending(client, monkeypatch)
    manual = admin_client.post(
        "/api/v1/questions",
        json={"question": "手動のラン対象", "answer": "回答"},
    ).json()["id"]
    from physics_ai_tutor.services import ai_review_service as service

    eligible = service.eligible_question_ids(
        db, "selected", question_ids=[ids[0], manual, ids[2], 99999]
    )

    assert eligible == [ids[0], ids[2]]


def test_timed_out_run_is_failed_and_replaced(client, db, monkeypatch):
    _three_pending(client, monkeypatch)
    from datetime import UTC, datetime, timedelta

    from physics_ai_tutor.models import AiReviewRun
    from physics_ai_tutor.services import ai_review_service as service

    stuck = service.start_run(db, scope="pending", trigger="cli")
    db.query(AiReviewRun).filter_by(id=stuck.id).update(
        {"started_at": datetime.now(UTC) - timedelta(hours=1)}
    )
    db.commit()

    fresh = service.start_run(db, scope="pending", trigger="manual")

    stale_row = db.get(AiReviewRun, stuck.id)
    assert stale_row.status == "failed"
    assert "timed out" in stale_row.error
    assert fresh.status == "running"


def test_run_endpoints(client, user_client, admin_client, db, monkeypatch):
    RUNS = "/api/v1/admin/ai-review/runs"
    COUNT = "/api/v1/admin/ai-review/pending-count"
    assert client.post(RUNS, json={"scope": "pending"}).status_code == 401
    assert user_client.get(COUNT).status_code == 403

    _three_pending(client, monkeypatch)
    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        fake_generation(json.dumps(VALID_REVIEW)),
    )

    preview = admin_client.get(COUNT).json()
    assert preview["pending"] == 3
    assert preview["remaining"] == settings.ai_review_daily_cap

    started = admin_client.post(RUNS, json={"scope": "pending"})
    assert started.status_code == 202
    run_id = started.json()["id"]

    # TestClient executes background tasks before returning, so it is done.
    polled = admin_client.get(f"{RUNS}/{run_id}").json()
    assert polled["status"] == "done"
    assert polled["reviewed_count"] == 3
    assert polled["trigger"] == "manual"
    assert polled["started_by_user_id"] is not None

    listed = admin_client.get(RUNS).json()
    assert [run["id"] for run in listed] == [run_id]
    assert admin_client.get(f"{RUNS}/9999").status_code == 404


def test_run_endpoint_conflict_returns_409(client, admin_client, db, monkeypatch):
    _three_pending(client, monkeypatch)
    from physics_ai_tutor.services import ai_review_service as service

    service.start_run(db, scope="pending", trigger="cli")

    response = admin_client.post(
        "/api/v1/admin/ai-review/runs", json={"scope": "pending"}
    )

    assert response.status_code == 409
