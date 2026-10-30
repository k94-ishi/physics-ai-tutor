from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from physics_ai_tutor.cli import review_metrics as metrics_cli
from physics_ai_tutor.models import AiReview, QuestionReview
from physics_ai_tutor.repositories import (
    ai_review_repository,
    review_metrics_repository,
)
from physics_ai_tutor.repositories.review_metrics_repository import ReviewPair
from physics_ai_tutor.schemas.ai_review import AiReviewCreate, AiReviewVerdict
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question_review import QuestionReviewReason
from physics_ai_tutor.services import deepseek_service, review_metrics_service
from tests.conftest import engine, fake_generation

ASK_PATH = "/api/v1/ai/ask"
QUESTIONS = "/api/v1/questions"
AGREEMENT_PATH = "/api/v1/admin/stats/review-agreement"

NOW = datetime(2026, 11, 5, tzinfo=UTC)


def _pair(ai, human, confidence=0.9, human_reason=None, ai_reasons=(), **kw):
    defaults = dict(
        question_id=1,
        human_action=human,
        human_reason=human_reason,
        ai_verdict=ai,
        ai_confidence=confidence,
        ai_reasons=tuple(ai_reasons),
        answer_prompt_version="v2",
        reviewer_prompt_version="r1",
        reviewed_at=NOW,
    )
    defaults.update(kw)
    return ReviewPair(**defaults)


# Ten pairs with hand-computed expectations:
#   AI REJECT x4: human REJECT x3, APPROVE x1  -> reject precision 3/4
#   AI APPROVE x3: human APPROVE x2, REJECT x1
#   AI EDIT x2: human EDIT_APPROVE x1, APPROVE x1
#   unparsed x1: human REJECT
# Human REJECT total = 3 + 1 + 1 = 5 -> reject recall 3/5
# Exact agreement = 3 + 2 + 1 = 6/10; publish agreement = 7/10
TEN_PAIRS = [
    _pair("REJECT", "REJECT", 0.95, "OFF_TOPIC", ["OFF_TOPIC"]),
    _pair("REJECT", "REJECT", 0.9, "PHYSICS_ERROR", ["MATH_ERROR"]),
    _pair("REJECT", "REJECT", 0.85),
    _pair("REJECT", "APPROVE", 0.6),
    _pair("APPROVE", "APPROVE", 0.8),
    _pair("APPROVE", "APPROVE", 0.7),
    _pair("APPROVE", "REJECT", 0.75, "INCOMPLETE", []),
    _pair("EDIT", "EDIT_APPROVE", 0.65, "INCOMPLETE", ["INCOMPLETE", "UNCLEAR"]),
    _pair("EDIT", "APPROVE", 0.4),
    _pair(None, "REJECT", None),
]


def test_metrics_match_hand_computation():
    metrics = review_metrics_service.compute_agreement(TEN_PAIRS)

    assert metrics.n == 10
    assert metrics.sufficient is False
    assert metrics.exact_agreement_rate == pytest.approx(0.6)
    assert metrics.publish_agreement_rate == pytest.approx(0.7)
    assert metrics.reject_precision == pytest.approx(3 / 4)
    assert metrics.reject_recall == pytest.approx(3 / 5)

    matrix = metrics.confusion_matrix
    assert matrix["REJECT"] == {"APPROVE": 1, "EDIT_APPROVE": 0, "REJECT": 3}
    assert matrix["APPROVE"] == {"APPROVE": 2, "EDIT_APPROVE": 0, "REJECT": 1}
    assert matrix["EDIT"] == {"APPROVE": 1, "EDIT_APPROVE": 1, "REJECT": 0}
    assert matrix["UNPARSED"] == {"APPROVE": 0, "EDIT_APPROVE": 0, "REJECT": 1}

    # Jaccard over the three pairs where both sides gave reasons:
    # {OFF_TOPIC}/{OFF_TOPIC}=1, {PHYSICS_ERROR}/{MATH_ERROR}=0,
    # {INCOMPLETE}/{INCOMPLETE,UNCLEAR}=1/2 -> mean 0.5
    assert metrics.reason_jaccard_mean == pytest.approx(0.5)


def test_calibration_buckets_by_confidence_decile():
    metrics = review_metrics_service.compute_agreement(TEN_PAIRS)
    by_low = {bucket.low: bucket for bucket in metrics.calibration}

    # 0.9 and 0.95 -> decile 0.9: both agreed.
    assert by_low[0.9].n == 2
    assert by_low[0.9].agreement_rate == pytest.approx(1.0)
    # 0.6 (REJECT/APPROVE: no) and 0.65 (EDIT/EDIT_APPROVE: yes) -> 0.5
    assert by_low[0.6].n == 2
    assert by_low[0.6].agreement_rate == pytest.approx(0.5)
    # The verdict-less pair has no confidence and is not bucketed.
    assert sum(bucket.n for bucket in metrics.calibration) == 9


def test_confidence_of_exactly_one_lands_in_the_top_bucket():
    metrics = review_metrics_service.compute_agreement([_pair("REJECT", "REJECT", 1.0)])

    assert [b.low for b in metrics.calibration] == [0.9]


def test_sufficient_flag_at_thirty_pairs():
    pairs = [_pair("APPROVE", "APPROVE") for _ in range(30)]

    assert review_metrics_service.compute_agreement(pairs).sufficient is True
    assert review_metrics_service.compute_agreement(pairs[:29]).sufficient is False


def test_empty_input_yields_null_rates():
    metrics = review_metrics_service.compute_agreement([])

    assert metrics.n == 0
    assert metrics.exact_agreement_rate is None
    assert metrics.reject_precision is None
    assert metrics.calibration == []


# --- pairing against the database ---------------------------------------------


def _ask(client, monkeypatch, text):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))
    return client.post(ASK_PATH, json={"question": text}).json()["question_id"]


def _ai_review(db, question_id, verdict, confidence=0.9, created_at=None, version="r1"):
    row = ai_review_repository.create(
        db,
        AiReviewCreate(
            question_id=question_id,
            language=Language.JA,
            verdict=verdict,
            confidence=confidence,
            reasons=[QuestionReviewReason.OFF_TOPIC],
            model="mock",
            prompt_version=version,
        ),
    )
    db.commit()
    if created_at is not None:
        db.query(AiReview).filter_by(id=row.id).update({"created_at": created_at})
        db.commit()
    return row


def _human_review(admin_client, question_id, action, reason=None):
    body = {"action": action}
    if reason:
        body["reason"] = reason
    response = admin_client.post(f"{QUESTIONS}/{question_id}/review", json=body)
    assert response.status_code == 200


def test_pairs_use_the_latest_ai_review_before_the_human_one(
    client, admin_client, db, monkeypatch
):
    question_id = _ask(client, monkeypatch, "ペアリングの質問です")
    earlier = datetime.now(UTC) - timedelta(hours=2)
    _ai_review(db, question_id, AiReviewVerdict.APPROVE, 0.5, created_at=earlier)
    _ai_review(
        db,
        question_id,
        AiReviewVerdict.REJECT,
        0.9,
        created_at=earlier + timedelta(hours=1),
    )

    _human_review(admin_client, question_id, "REJECT", "OFF_TOPIC")

    pairs = review_metrics_repository.list_pairs(db, None)

    assert len(pairs) == 1
    assert pairs[0].ai_verdict == "REJECT"
    assert pairs[0].human_action == "REJECT"
    assert pairs[0].answer_prompt_version is not None


def test_human_review_before_any_ai_review_is_excluded(
    client, admin_client, db, monkeypatch
):
    question_id = _ask(client, monkeypatch, "先に人が見た質問です")
    _human_review(admin_client, question_id, "APPROVE")
    # The AI verdict arrives afterwards (e.g. a later backfill).
    _ai_review(db, question_id, AiReviewVerdict.APPROVE)

    assert review_metrics_repository.list_pairs(db, None) == []


def test_pairs_respect_since_and_reviewer_kind(client, admin_client, db, monkeypatch):
    question_id = _ask(client, monkeypatch, "期間フィルタの質問です")
    _ai_review(
        db,
        question_id,
        AiReviewVerdict.APPROVE,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    _human_review(admin_client, question_id, "APPROVE")
    db.query(QuestionReview).update({"created_at": datetime(2026, 1, 2, tzinfo=UTC)})
    db.commit()

    assert len(review_metrics_repository.list_pairs(db, None)) == 1
    later = datetime(2026, 6, 1, tzinfo=UTC)
    assert review_metrics_repository.list_pairs(db, later) == []

    db.query(QuestionReview).update({"reviewer_kind": "policy"})
    db.commit()
    assert review_metrics_repository.list_pairs(db, None) == []


def test_report_groups_by_prompt_versions(client, admin_client, db, monkeypatch):
    first = _ask(client, monkeypatch, "r1で判定された質問です")
    second = _ask(client, monkeypatch, "r2で判定された質問です")
    _ai_review(db, first, AiReviewVerdict.APPROVE, version="r1")
    _ai_review(db, second, AiReviewVerdict.REJECT, version="r2")
    _human_review(admin_client, first, "APPROVE")
    _human_review(admin_client, second, "APPROVE")

    report = review_metrics_service.build_report(db, None)

    assert report.overall.n == 2
    assert set(report.by_reviewer_prompt_version) == {"r1", "r2"}
    assert report.by_reviewer_prompt_version["r1"].exact_agreement_rate == 1.0
    assert report.by_reviewer_prompt_version["r2"].exact_agreement_rate == 0.0
    # Both answers came from the current answer prompt version.
    assert list(report.by_answer_prompt_version) == ["v2"]
    assert len(report.by_month) == 1


def test_endpoint_is_admin_only_and_returns_the_report(
    client, user_client, admin_client, db, monkeypatch
):
    assert client.get(AGREEMENT_PATH).status_code == 401
    assert user_client.get(AGREEMENT_PATH).status_code == 403

    question_id = _ask(client, monkeypatch, "エンドポイントの質問です")
    _ai_review(db, question_id, AiReviewVerdict.REJECT, 0.9)
    _human_review(admin_client, question_id, "REJECT", "OFF_TOPIC")

    body = admin_client.get(AGREEMENT_PATH).json()

    assert body["overall"]["n"] == 1
    assert body["overall"]["sufficient"] is False
    assert body["overall"]["confusion_matrix"]["REJECT"]["REJECT"] == 1
    assert body["overall"]["reject_precision"] == 1.0
    assert body["since"] is not None


@pytest.fixture
def _bind_metrics_cli(monkeypatch, db):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(metrics_cli, "SessionLocal", factory)


def test_cli_prints_tables(
    client, admin_client, db, monkeypatch, _bind_metrics_cli, capsys
):
    question_id = _ask(client, monkeypatch, "CLI集計の質問です")
    _ai_review(db, question_id, AiReviewVerdict.REJECT, 0.9)
    _human_review(admin_client, question_id, "REJECT", "OFF_TOPIC")

    assert metrics_cli.main(include_all=True) == 1

    out = capsys.readouterr().out
    assert "== overall (n=1)  [n too small]" in out
    assert "reject precision 100.0%" in out
    assert "reviewer prompt r1" in out
    assert "0.9-1.0" in out
