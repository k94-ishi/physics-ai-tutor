import json
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from physics_ai_tutor.cli import create_user as create_user_cli
from physics_ai_tutor.cli import translate_missing as translate_cli
from physics_ai_tutor.database import seed as seed_module
from physics_ai_tutor.models import Question, User
from physics_ai_tutor.services.embedding_service import (
    create_embeddings as real_create_embeddings,
)
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
        if entry.get("question_en") and "en_provenance" not in entry
    }
    assert len(hand_translated) == 21
    assert all(q.question_en is not None for q in questions)
    assert all(q.ja_provenance == "ORIGINAL" for q in questions)
    # Hand translations stay HUMAN; stored machine ones keep MACHINE.
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


def test_seed_file_carries_levels_for_every_entry():
    # Fresh stacks need ratings for the two-axis grid without an LLM call ([42]).
    for entry in _seed_file_entries():
        assert 0 <= entry["physics_level"] <= 4
        assert 0 <= entry["math_level"] <= 4


def test_seed_levels_override_extracted_levels(db, _bind_cli_sessions):
    seed_module.seed()

    by_text = {q.question_ja: q for q in db.query(Question).all()}
    for entry in _seed_file_entries():
        question = by_text[entry["question_ja"]]
        assert question.physics_level == entry["physics_level"]
        assert question.math_level == entry["math_level"]


def test_seed_needs_no_deepseek_call(db, _bind_cli_sessions, monkeypatch):
    # Translations and tags come from the file, so DeepSeek is never asked.
    from physics_ai_tutor.services import concept_service, translation_service

    def _forbidden(*args, **kwargs):
        raise AssertionError("seed must not call DeepSeek")

    monkeypatch.setattr(concept_service, "extract_concept_names", _forbidden)
    monkeypatch.setattr(translation_service, "translate_qa", _forbidden)

    seed_module.seed()

    entries = _seed_file_entries()
    by_text = {q.question_ja: q for q in db.query(Question).all()}
    for entry in entries:
        question = by_text[entry["question_ja"]]
        assert question.question_en == entry["question_en"]
        assert question.en_provenance == entry.get("en_provenance", "HUMAN")


def test_export_seed_round_trips_the_seed_file(db, _bind_cli_sessions):
    from physics_ai_tutor.cli import export_seed

    seed_module.seed()
    entries = _seed_file_entries()

    exported, notes = export_seed.build_entries(
        db, [entry["question_ja"] for entry in entries]
    )

    assert exported == entries
    assert notes == []


def test_seed_needs_no_openai_call_either(db, _bind_cli_sessions, monkeypatch):
    # Every vector the seed asks for is in seed_embeddings.jsonl.gz ([55]).
    from physics_ai_tutor.models import Concept, QuestionEmbedding
    from physics_ai_tutor.services import embedding_service

    def _forbidden(texts):
        raise AssertionError(f"seed must not call OpenAI: {texts[:1]}")

    monkeypatch.setattr(embedding_service, "create_embeddings", real_create_embeddings)
    monkeypatch.setattr(embedding_service, "_request_embeddings", _forbidden)

    seed_module.seed()

    assert db.query(QuestionEmbedding).count() == 4 * len(_seed_file_entries())
    assert db.query(Concept).count() > 0
    # The preloaded vectors are released after seeding.
    assert embedding_service._preloaded == {}


def test_export_seed_embeddings_round_trips(db, _bind_cli_sessions, monkeypatch):
    from physics_ai_tutor.cli import export_seed_embeddings
    from physics_ai_tutor.core.config import settings
    from physics_ai_tutor.database import seed_embeddings
    from physics_ai_tutor.services import embedding_service

    monkeypatch.setattr(embedding_service, "create_embeddings", real_create_embeddings)
    stored = seed_embeddings.read(
        seed_embeddings.EMBEDDINGS_FILE, settings.embedding_model
    )
    seed_module.seed()

    exported = export_seed_embeddings.collect(db, settings.embedding_model)

    assert exported.keys() == stored.keys()
    # pgvector prints float32 as short decimals; compare at float32 precision.
    as_f32 = seed_embeddings._encode
    assert all(as_f32(exported[key]) == as_f32(stored[key]) for key in stored)


def test_embeddings_file_for_another_model_is_ignored(tmp_path):
    from physics_ai_tutor.database import seed_embeddings

    path = tmp_path / "v.jsonl.gz"
    seed_embeddings.write(path, "model-a", {"k": [0.5, -1.0]})

    assert seed_embeddings.read(path, "model-a") == {"k": [0.5, -1.0]}
    assert seed_embeddings.read(path, "model-b") == {}
