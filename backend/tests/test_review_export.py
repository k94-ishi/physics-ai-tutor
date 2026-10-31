import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from physics_ai_tutor.cli import export_reviews as export_cli
from physics_ai_tutor.models import QuestionReview
from physics_ai_tutor.services import deepseek_service, review_export_service
from tests.conftest import engine, fake_generation

ASK_PATH = "/api/v1/ai/ask"
QUESTIONS = "/api/v1/questions"
EXPORT_PATH = "/api/v1/admin/reviews/export"


def _ask_and_edit_approve(client, admin_client, monkeypatch, text="輸出テスト質問"):
    monkeypatch.setattr(
        deepseek_service, "generate_answer", fake_generation("元の回答")
    )
    question_id = client.post(ASK_PATH, json={"question": text}).json()["question_id"]

    review = admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={
            "action": "EDIT_APPROVE",
            "language": "ja",
            "question": text,
            "answer": "先生が直した回答",
            "reason": "PHYSICS_ERROR",
            "comment": "符号の誤り",
        },
    )
    assert review.status_code == 200

    return question_id


def _parse(body: str) -> list[dict]:
    return [json.loads(line) for line in body.splitlines() if line]


def test_export_line_carries_diff_reason_and_generation_metadata(
    client, admin_client, monkeypatch
):
    question_id = _ask_and_edit_approve(client, admin_client, monkeypatch)

    response = admin_client.get(EXPORT_PATH)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")

    rows = _parse(response.text)
    assert len(rows) == 1
    row = rows[0]

    assert list(row.keys()) == review_export_service.EXPORT_FIELDS
    assert row["question_id"] == question_id
    assert row["action"] == "EDIT_APPROVE"
    assert row["reason"] == "PHYSICS_ERROR"
    assert row["comment"] == "符号の誤り"
    assert row["answer_before"] == "元の回答"
    assert row["answer_after"] == "先生が直した回答"
    assert row["generation_model"] == "mock-model"
    assert row["generation_mode"] == "DIRECT"
    assert row["prompt_version"] is not None
    assert row["source"] == "AI_GENERATED"
    assert row["reviewer_kind"] == "human"
    # Approval triggered concept extraction (mocked in conftest).
    assert "概念A" in row["concepts"]


def test_export_pseudonymises_the_reviewer(client, admin_client, monkeypatch):
    _ask_and_edit_approve(client, admin_client, monkeypatch)

    body = admin_client.get(EXPORT_PATH).text
    row = _parse(body)[0]

    assert "reviewer_id" not in row
    assert "@" not in body
    assert len(row["reviewer_hash"]) == 16
    assert int(row["reviewer_hash"], 16) >= 0
    # Stable across exports; distinct from a different reviewer id.
    hash_of = review_export_service.reviewer_hash
    assert hash_of(1) == hash_of(1)
    assert hash_of(1) != hash_of(2)
    assert hash_of(None) is None


def test_export_excludes_rows_before_cutoff_unless_all(
    client, admin_client, db, monkeypatch
):
    _ask_and_edit_approve(client, admin_client, monkeypatch)

    # Backdate the review to before the data cutoff.
    db.query(QuestionReview).update({"created_at": datetime(2026, 10, 1, tzinfo=UTC)})
    db.commit()

    default = _parse(admin_client.get(EXPORT_PATH).text)
    everything = _parse(admin_client.get(EXPORT_PATH, params={"all": "true"}).text)
    explicit = _parse(
        admin_client.get(EXPORT_PATH, params={"since": "2026-09-01"}).text
    )

    assert default == []
    assert len(everything) == 1
    assert len(explicit) == 1


def test_export_since_is_inclusive_by_day(client, admin_client, monkeypatch):
    _ask_and_edit_approve(client, admin_client, monkeypatch)
    today = datetime.now(UTC).date()

    rows_today = _parse(
        admin_client.get(EXPORT_PATH, params={"since": today.isoformat()}).text
    )
    rows_tomorrow = _parse(
        admin_client.get(
            EXPORT_PATH, params={"since": (today + timedelta(days=1)).isoformat()}
        ).text
    )

    assert len(rows_today) == 1
    assert rows_tomorrow == []


def test_export_requires_admin(client, user_client):
    assert client.get(EXPORT_PATH).status_code == 401
    assert user_client.get(EXPORT_PATH).status_code == 403


@pytest.fixture
def _bind_export_cli(monkeypatch, db):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(export_cli, "SessionLocal", factory)


def test_cli_writes_jsonl_file(
    client, admin_client, monkeypatch, tmp_path, _bind_export_cli, capsys
):
    _ask_and_edit_approve(client, admin_client, monkeypatch, "CLI輸出テスト")
    out = tmp_path / "reviews.jsonl"

    count = export_cli.main(out=str(out))

    assert count == 1
    assert "Exported 1 reviews" in capsys.readouterr().err
    text = out.read_text(encoding="utf-8")
    assert _parse(text)[0]["question_after"] == "CLI輸出テスト"
    # Non-ASCII stays readable instead of being escaped.
    assert "CLI輸出テスト" in text


def test_cli_all_flag_ignores_cutoff(
    client, admin_client, db, monkeypatch, tmp_path, _bind_export_cli
):
    _ask_and_edit_approve(client, admin_client, monkeypatch)
    db.query(QuestionReview).update({"created_at": datetime(2026, 1, 1, tzinfo=UTC)})
    db.commit()

    assert export_cli.main(out=str(tmp_path / "a.jsonl")) == 0
    assert export_cli.main(include_all=True, out=str(tmp_path / "b.jsonl")) == 1


def test_cli_parses_arguments():
    args = export_cli.parse_args(["--since", "2026-10-28", "--out", "x.jsonl"])

    assert args.since.isoformat() == "2026-10-28"
    assert args.out == "x.jsonl"
    assert args.all is False


def test_export_carries_the_ai_verdict_the_teacher_could_see(
    client, admin_client, db, monkeypatch
):
    from physics_ai_tutor.repositories import ai_review_repository
    from physics_ai_tutor.schemas.ai_review import AiReviewCreate, AiReviewVerdict
    from physics_ai_tutor.schemas.language import Language
    from physics_ai_tutor.schemas.question_review import QuestionReviewReason

    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))
    question_id = client.post(ASK_PATH, json={"question": "AI付き輸出の質問"}).json()[
        "question_id"
    ]
    ai_review_repository.create(
        db,
        AiReviewCreate(
            question_id=question_id,
            language=Language.JA,
            verdict=AiReviewVerdict.REJECT,
            confidence=0.9,
            reasons=[QuestionReviewReason.OFF_TOPIC],
            model="mock",
            prompt_version="r1",
        ),
    )
    db.commit()
    admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        json={"action": "REJECT", "reason": "OFF_TOPIC"},
    )

    row = _parse(admin_client.get(EXPORT_PATH).text)[0]

    assert row["ai_verdict"] == "REJECT"
    assert row["ai_confidence"] == 0.9
    assert row["ai_reasons"] == ["OFF_TOPIC"]
    assert row["ai_prompt_version"] == "r1"
    assert row["ai_reviewed_at"] is not None
    assert list(row.keys()) == review_export_service.EXPORT_FIELDS


def test_export_ai_fields_are_null_without_an_earlier_ai_review(
    client, admin_client, monkeypatch
):
    _ask_and_edit_approve(client, admin_client, monkeypatch)

    row = _parse(admin_client.get(EXPORT_PATH).text)[0]

    assert row["ai_verdict"] is None
    assert row["ai_prompt_version"] is None
