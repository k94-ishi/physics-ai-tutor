"""Two-axis difficulty ([40]): storage at extraction time, teacher edits,
public payload, and the backfill CLI."""

import pytest
from sqlalchemy.orm import sessionmaker

from physics_ai_tutor.cli import backfill_levels as backfill_cli
from physics_ai_tutor.models import Question
from physics_ai_tutor.services import concept_service
from tests.conftest import engine

QUESTIONS = "/api/v1/questions"
ASK = "/api/v1/ai/ask"

RATED = [
    "加速度 | acceleration",
    "LEVELS: question physics=1 math=0 | answer physics=1 math=1",
]


@pytest.fixture
def _rated_extraction(monkeypatch):
    monkeypatch.setattr(
        concept_service,
        "extract_concept_names",
        lambda question, answer, language="ja": RATED,
    )


def test_approval_stores_levels_and_payload_carries_them(
    client, admin_client, db, monkeypatch, _rated_extraction
):
    """Extraction (and with it the rating) runs when a question is APPROVED."""
    from physics_ai_tutor.services import deepseek_service
    from tests.conftest import fake_generation

    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("回答"))
    client.post(ASK, json={"question": "難易度が付く質問ですか？"})

    row = db.query(Question).one()
    assert row.question_physics_level is None, "unreviewed rows are not rated yet"

    admin_client.post(f"{QUESTIONS}/{row.id}/review", json={"action": "APPROVE"})
    db.refresh(row)
    assert (
        row.question_physics_level,
        row.question_math_level,
        row.answer_physics_level,
        row.answer_math_level,
    ) == (1, 0, 1, 1)

    body = admin_client.get(f"{QUESTIONS}/{row.id}").json()
    assert body["question_physics_level"] == 1
    assert body["answer_math_level"] == 1
    assert "LEVELS" not in " ".join(body["concepts"])


def test_teacher_can_correct_a_level_without_touching_the_text(admin_client, db):
    created = admin_client.post(
        QUESTIONS, json={"question": "難易度を直す質問", "answer": "回答"}
    ).json()

    response = admin_client.put(
        f"{QUESTIONS}/{created['id']}", json={"question_physics_level": 3}
    )

    assert response.status_code == 200
    assert response.json()["question_physics_level"] == 3
    row = db.get(Question, created["id"])
    assert row.question_physics_level == 3
    assert row.question_math_level is None, "unset axes stay untouched"


def test_levels_are_validated_on_update(admin_client):
    created = admin_client.post(
        QUESTIONS, json={"question": "範囲外の難易度", "answer": "回答"}
    ).json()

    assert (
        admin_client.put(
            f"{QUESTIONS}/{created['id']}", json={"question_math_level": 5}
        ).status_code
        == 422
    )


def test_backfill_cli_is_restartable_and_window_guarded(admin_client, db, monkeypatch):
    from datetime import UTC, datetime

    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(backfill_cli, "SessionLocal", factory)

    # Created (and auto-approved) while extraction still returns no LEVELS
    # line, like every pre-[40] production row: rated = NULL.
    for index in range(2):
        admin_client.post(
            QUESTIONS, json={"question": f"未評価の質問{index}", "answer": "回答"}
        )
    assert (
        db.query(Question).filter(Question.question_physics_level.isnot(None)).count()
        == 0
    )

    monkeypatch.setattr(
        concept_service,
        "extract_concept_names",
        lambda question, answer, language="ja": RATED,
    )

    # Outside the window nothing is rated.
    monkeypatch.setattr(
        backfill_cli, "_now", lambda: datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    )
    assert backfill_cli.main(limit=10) == 2
    assert (
        db.query(Question).filter(Question.question_physics_level.isnot(None)).count()
        == 0
    )

    # --force rates up to the limit; a second run continues where it stopped.
    assert backfill_cli.main(limit=1, force=True) == 0
    rated = db.query(Question).filter(Question.question_physics_level.isnot(None))
    assert rated.count() == 1

    assert backfill_cli.main(limit=10, force=True) == 0
    assert rated.count() == 2

    # Everything rated: the next run is a no-op success.
    assert backfill_cli.main(limit=10, force=True) == 0
