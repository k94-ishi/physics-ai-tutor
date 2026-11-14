import json

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import sessionmaker

from physics_ai_tutor.cli import create_user as create_user_cli
from physics_ai_tutor.cli import translate_missing as translate_cli
from physics_ai_tutor.database import seed as seed_module
from physics_ai_tutor.database import seed_file
from physics_ai_tutor.models import Question, User
from tests.conftest import async_engine, engine


@pytest.fixture
def _bind_cli_sessions(monkeypatch, db):
    # CLI entry points open their own session; bind them to the test engine.
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    async_factory = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    # create_user went async in [73] and the seed in [95].
    monkeypatch.setattr(create_user_cli, "AsyncSessionLocal", async_factory)
    monkeypatch.setattr(seed_module, "AsyncSessionLocal", async_factory)
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
    return seed_file.read_entries()


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


def test_seed_file_carries_levels_for_every_entry():
    # Fresh stacks need ratings for the two-axis grid without an LLM call ([42]).
    for entry in _seed_file_entries():
        assert 0 <= entry["physics_level"] <= 4
        assert 0 <= entry["math_level"] <= 4


def test_embeddings_file_for_another_model_is_ignored(tmp_path):
    from physics_ai_tutor.database import seed_embeddings

    path = tmp_path / "v.jsonl.gz"
    seed_embeddings.write(path, "model-a", {"k": [0.5, -1.0]})

    assert seed_embeddings.read(path, "model-a") == {"k": [0.5, -1.0]}
    assert seed_embeddings.read(path, "model-b") == {}


def test_seed_lines_are_valid_input_for_the_admin_upload(admin_client):
    """seed.jsonl doubles as an upload file; extra fields are ignored ([101])."""
    lines = [
        json.dumps(entry, ensure_ascii=False) for entry in _seed_file_entries()[:3]
    ]

    response = admin_client.post(
        "/api/v1/questions/import",
        files={"file": ("seed.jsonl", "\n".join(lines).encode(), "application/jsonl")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["created_count"] == 3
