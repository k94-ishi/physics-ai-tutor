"""The seed rebuilds a disposable database offline, and the exports round-trip."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from physics_ai_tutor.cli import export_seed, export_seed_embeddings
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database import seed as seed_module
from physics_ai_tutor.database import seed_embeddings
from physics_ai_tutor.models import Concept, Question, QuestionEmbedding
from physics_ai_tutor.services import (
    concept_service,
    embedding_service,
    translation_service,
)
from tests.conftest import async_engine, engine, reset_database
from tests.test_cli import _seed_file_entries


def _forbidden(*args, **kwargs):
    raise AssertionError("the seed must not call OpenAI or DeepSeek")


@pytest.fixture(scope="module")
def seeded():
    """Seed once for the module; every test below only reads."""
    reset_database()
    with pytest.MonkeyPatch.context() as patch:
        # The real create_embeddings serves the stored vectors; any request
        # that would reach OpenAI, and every DeepSeek entry point, fails.
        patch.setattr(
            seed_module,
            "AsyncSessionLocal",
            async_sessionmaker(bind=async_engine, expire_on_commit=False),
        )
        # The only path to OpenAI since [108]; any request fails the seed.
        patch.setattr(embedding_service, "_async_request_embeddings", _forbidden)
        patch.setattr(concept_service, "async_extract_concept_names", _forbidden)
        patch.setattr(translation_service, "async_translate_qa", _forbidden)
        seed_module.seed()
    with Session(engine) as session:
        yield session
    reset_database()


def _by_text(session: Session) -> dict[str | None, Question]:
    return {q.question_ja: q for q in session.query(Question).all()}


def test_seed_loads_every_entry_as_approved_manual(seeded):
    questions = seeded.query(Question).all()

    assert len(questions) == len(_seed_file_entries())
    assert {q.status for q in questions} == {"APPROVED"}
    assert {q.source for q in questions} == {"MANUAL"}


def test_seed_keeps_stored_translations_and_provenance(seeded):
    by_text = _by_text(seeded)
    hand = 0
    for entry in _seed_file_entries():
        question = by_text[entry["question_ja"]]
        assert question.ja_provenance == "ORIGINAL"
        assert question.question_en == entry["question_en"]
        expected = entry.get("en_provenance", "HUMAN")
        assert question.en_provenance == expected, entry["question_ja"]
        hand += expected == "HUMAN"
    assert hand == 21


def test_seed_levels_win_over_extraction(seeded):
    by_text = _by_text(seeded)
    for entry in _seed_file_entries():
        question = by_text[entry["question_ja"]]
        assert (question.physics_level, question.math_level) == (
            entry["physics_level"],
            entry["math_level"],
        )


def test_seed_builds_embeddings_and_concepts_from_the_files(seeded):
    assert seeded.query(QuestionEmbedding).count() == 4 * len(_seed_file_entries())
    assert seeded.query(Concept).count() > 0
    # The preloaded vectors are released after seeding.
    assert embedding_service._preloaded == {}


@pytest.mark.anyio
async def test_export_seed_reproduces_the_seed_file(seeded):
    entries = _seed_file_entries()

    # Not `async_db`: that fixture would empty the module's seeded tables.
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        exported, notes = await export_seed.build_entries(
            session, [entry["question_ja"] for entry in entries]
        )

    assert exported == entries
    assert notes == []


@pytest.mark.anyio
async def test_export_seed_embeddings_reproduces_the_vectors(seeded):
    stored = seed_embeddings.read(
        seed_embeddings.EMBEDDINGS_FILE, settings.embedding_model
    )

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        exported = await export_seed_embeddings.collect(
            session, settings.embedding_model
        )

    assert exported.keys() == stored.keys()
    # pgvector prints float32 as short decimals; compare at float32 precision.
    encode = seed_embeddings._encode
    assert all(encode(exported[key]) == encode(stored[key]) for key in stored)
