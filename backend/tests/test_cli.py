import json
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from physics_ai_tutor.cli import create_user as create_user_cli
from physics_ai_tutor.cli import translate_missing as translate_cli
from physics_ai_tutor.database import seed as seed_module
from physics_ai_tutor.models import Question, User
from tests.conftest import engine


@pytest.fixture
def _bind_cli_sessions(monkeypatch, db):
    # CLI entry points open their own session; bind them to the test engine.
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(create_user_cli, "SessionLocal", factory)
    monkeypatch.setattr(seed_module, "SessionLocal", factory)
    monkeypatch.setattr(translate_cli, "SessionLocal", factory)


def test_create_user_cli_creates_admin(db, _bind_cli_sessions, capsys):
    create_user_cli.main("cli-admin@example.com", "clipassword1", "admin")

    user = db.query(User).filter_by(email="cli-admin@example.com").one()
    assert user.role == "admin"
    assert user.hashed_password != "clipassword1"
    assert "Created user" in capsys.readouterr().out


def test_create_user_cli_rejects_duplicate_email(db, _bind_cli_sessions):
    create_user_cli.main("dup@example.com", "clipassword1", "user")

    with pytest.raises(SystemExit) as exc:
        create_user_cli.main("dup@example.com", "clipassword1", "user")

    assert exc.value.code == 1


def test_create_user_cli_rejects_invalid_email(db, _bind_cli_sessions):
    with pytest.raises(SystemExit) as exc:
        create_user_cli.main("not-an-email", "clipassword1", "user")

    assert exc.value.code == 1


def _seed_file_entries() -> list[dict]:
    seed_file = Path(seed_module.__file__).resolve().parent / "seed.json"

    with open(seed_file, encoding="utf-8") as f:
        return json.load(f)


def test_seed_loads_all_questions_as_approved(db, _bind_cli_sessions):
    seed_module.seed()

    questions = db.query(Question).all()
    assert len(questions) == len(_seed_file_entries())
    assert all(q.status == "APPROVED" for q in questions)
    assert all(q.source == "MANUAL" for q in questions)


def test_seed_file_has_no_duplicate_questions():
    # Duplicate texts would make the all-or-nothing seed fail entirely.
    entries = _seed_file_entries()

    for key in ("question_ja", "question_en"):
        texts = [entry[key] for entry in entries if entry.get(key)]
        assert len(texts) == len(set(texts)), key


def test_seed_file_mixes_hand_translated_and_production_entries():
    # 21 hand-translated pairs plus teacher-approved production Q&A (Japanese
    # only; the other language is machine translated on import).
    entries = _seed_file_entries()

    assert len(entries) >= 100
    assert sum(1 for entry in entries if entry.get("question_en")) >= 21
    assert all(entry["question_ja"] and entry["answer_ja"] for entry in entries)


def test_seed_keeps_hand_translations(db, _bind_cli_sessions):
    seed_module.seed()

    questions = db.query(Question).all()
    hand_translated = {
        entry["question_ja"]
        for entry in _seed_file_entries()
        if entry.get("question_en")
    }
    assert all(q.question_en is not None for q in questions)
    assert all(q.ja_provenance == "ORIGINAL" for q in questions)
    # Hand translations stay HUMAN; production entries get MACHINE ones.
    for q in questions:
        expected = "HUMAN" if q.question_ja in hand_translated else "MACHINE"
        assert q.en_provenance == expected, q.question_ja


def test_translate_missing_cli_fills_legacy_rows(db, _bind_cli_sessions, capsys):
    legacy = Question(question_ja="古い", answer_ja="回答", ja_provenance="ORIGINAL")
    db.add(legacy)
    db.commit()

    exit_code = translate_cli.main(language=None, limit=None, dry_run=False)

    assert exit_code == 0
    assert "translated: id=" in capsys.readouterr().out
    db.refresh(legacy)
    assert legacy.question_en == "[en] 古い"


def test_translate_missing_cli_dry_run_changes_nothing(db, _bind_cli_sessions, capsys):
    legacy = Question(question_ja="古い", answer_ja="回答", ja_provenance="ORIGINAL")
    db.add(legacy)
    db.commit()

    exit_code = translate_cli.main(language="en", limit=None, dry_run=True)

    assert exit_code == 0
    assert "would translate" in capsys.readouterr().out
    db.refresh(legacy)
    assert legacy.question_en is None
