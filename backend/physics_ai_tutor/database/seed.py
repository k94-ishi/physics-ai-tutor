"""Load seed.json into an empty database ([40], [53], [55]).

Everything an LLM produced and a teacher may rely on is stored in the
file, so a disposable local stack can be rebuilt without DeepSeek:
machine translations (with their provenance), tags (`"<ja> | <en>"`
pairs, the extraction format) and the two difficulty levels. The
embeddings live in seed_embeddings.jsonl.gz next to it, so a rebuild
needs no OpenAI call either; any vector missing there (new text, another
embedding model) is fetched from OpenAI. Entries without `tags` fall back
to concept extraction (DeepSeek).
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database import seed_embeddings
from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.database.transaction import transaction
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.schemas.language import TextProvenance
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionSource,
    QuestionStatus,
)
from physics_ai_tutor.services import (
    concept_service,
    embedding_service,
    question_service,
)


class SeedExtras(BaseModel):
    """The non-text fields of a seed entry."""

    physics_level: int | None = Field(default=None, ge=0, le=4)
    math_level: int | None = Field(default=None, ge=0, le=4)
    ja_provenance: TextProvenance | None = None
    en_provenance: TextProvenance | None = None
    tags: list[str] | None = None


EXTRA_KEYS = tuple(SeedExtras.model_fields)


def load_seed_file(seed_file: Path) -> list[tuple[QuestionCreate, SeedExtras]]:
    """Read seed.json into question texts plus their stored extras.

    Entries may use `question`/`answer` (Japanese) or the explicit
    `question_ja`/`answer_ja`/`question_en`/`answer_en` columns; missing
    languages are machine translated on import.
    """
    with open(seed_file, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for entry in data:
        extras = {key: entry.pop(key) for key in EXTRA_KEYS if key in entry}
        rows.append((QuestionCreate(**entry), SeedExtras(**extras)))
    return rows


def load_seed_entries(seed_file: Path) -> list[QuestionCreate]:
    return [question for question, _ in load_seed_file(seed_file)]


def apply_seed_extras(db, question: Question, extras: SeedExtras) -> None:
    """Attach stored tags, then let stored values win over computed ones."""
    if extras.tags is None:
        question_service.extract_concepts_best_effort(db, question)
    else:
        concept_service.attach_concepts_to_question(
            db, question.id, extras.tags, language=question.original_language
        )

    # After extraction, which writes levels of its own.
    if extras.physics_level is not None:
        question.physics_level = extras.physics_level
    if extras.math_level is not None:
        question.math_level = extras.math_level
    if extras.ja_provenance is not None and question.question_ja is not None:
        question.ja_provenance = extras.ja_provenance
    if extras.en_provenance is not None and question.question_en is not None:
        question.en_provenance = extras.en_provenance


def seed():
    seed_file = Path(__file__).resolve().parent / "seed.json"
    rows = load_seed_file(seed_file)

    embedding_service.preload(
        seed_embeddings.read(seed_embeddings.EMBEDDINGS_FILE, settings.embedding_model)
    )
    db = SessionLocal()

    try:
        questions = question_service.import_questions_from_jsonl(
            db,
            [question for question, _ in rows],
            status=QuestionStatus.APPROVED,
            source=QuestionSource.MANUAL,
            extract_concepts=False,
        )
        with transaction(db, "seed_extras"):
            for question, (_, extras) in zip(questions, rows, strict=True):
                apply_seed_extras(db, question, extras)
    finally:
        db.close()
        embedding_service.clear_preloaded()


if __name__ == "__main__":
    seed()
