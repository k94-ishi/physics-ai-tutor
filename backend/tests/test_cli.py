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
    texts = [entry["question"] for entry in _seed_file_entries()]

    assert len(texts) == len(set(texts))


def test_seed_translates_every_entry(db, _bind_cli_sessions):
    seed_module.seed()

    questions = db.query(Question).all()
    assert all(q.question_en is not None for q in questions)
    assert all(q.en_provenance == "MACHINE" for q in questions)


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
