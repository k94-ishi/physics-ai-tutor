"""Load seed.jsonl into an empty database ([40], [53], [55], [101]).

Everything an LLM produced and a teacher may rely on is stored in the
file, so a disposable local stack can be rebuilt without DeepSeek:
machine translations (with their provenance), tags (`"<ja> | <en>"`
pairs, the extraction format) and the two difficulty levels. The
embeddings live in seed_embeddings.jsonl.gz next to it, so a rebuild
needs no OpenAI call either; any vector missing there (new text, another
embedding model) is fetched from OpenAI. Entries without `tags` fall back
to concept extraction (DeepSeek).
"""

import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import ConceptExtractionError
from physics_ai_tutor.database import seed_embeddings
from physics_ai_tutor.database import seed_file as seed_file_module
from physics_ai_tutor.database.database import AsyncSessionLocal
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
    question_write_service,
)


class SeedExtras(BaseModel):
    """The non-text fields of a seed entry."""

    physics_level: int | None = Field(default=None, ge=0, le=4)
    math_level: int | None = Field(default=None, ge=0, le=4)
    ja_provenance: TextProvenance | None = None
    en_provenance: TextProvenance | None = None
    tags: list[str] | None = None


EXTRA_KEYS = tuple(SeedExtras.model_fields)


def load_seed_file(
    seed_file: Path = seed_file_module.SEED_FILE,
) -> list[tuple[QuestionCreate, SeedExtras]]:
    """Read seed.jsonl into question texts plus their stored extras.

    Entries may use `question`/`answer` (Japanese) or the explicit
    `question_ja`/`answer_ja`/`question_en`/`answer_en` columns; missing
    languages are machine translated on import.
    """
    data = seed_file_module.read_entries(seed_file)

    rows = []
    for entry in data:
        extras = {key: entry.pop(key) for key in EXTRA_KEYS if key in entry}
        rows.append((QuestionCreate(**entry), SeedExtras(**extras)))
    return rows


def apply_stored_values(question: Question, extras: SeedExtras) -> None:
    """Stored levels and provenance win over computed ones."""
    if extras.physics_level is not None:
        question.physics_level = extras.physics_level
    if extras.math_level is not None:
        question.math_level = extras.math_level
    if extras.ja_provenance is not None and question.question_ja is not None:
        question.ja_provenance = extras.ja_provenance
    if extras.en_provenance is not None and question.question_en is not None:
        question.en_provenance = extras.en_provenance


async def _tag_names(question: Question, extras: SeedExtras) -> list[str] | None:
    """Stored tags, or extracted ones for an entry without (DeepSeek)."""
    if extras.tags is not None:
        return extras.tags
    try:
        return await concept_service.extract_concept_names(
            *question.original_text(), language=question.original_language
        )
    except ConceptExtractionError:
        return None


async def _seed(rows: list[tuple[QuestionCreate, SeedExtras]]) -> None:
    """Import, then tags and stored values; one session, no AI call in a write."""
    async with AsyncSessionLocal() as session:
        questions = await question_write_service.import_questions_from_jsonl(
            session,
            [question for question, _ in rows],
            status=QuestionStatus.APPROVED,
            source=QuestionSource.MANUAL,
            extract_concepts=False,
        )
        extras = [extra for _, extra in rows]
        names = [
            await _tag_names(question, extra)
            for question, extra in zip(questions, extras, strict=True)
        ]
        # One index for every row, as in import: a shared tag is made once.
        plans = await concept_service.prepare_concepts_many(
            session,
            [
                (row_names or [], question.original_language)
                for row_names, question in zip(names, questions, strict=True)
            ],
        )
        async with transaction(session, "seed_extras"):
            for question, extra, row_names, plan in zip(
                questions, extras, names, plans, strict=True
            ):
                if row_names is not None:
                    await concept_service.apply_concepts(session, question.id, plan)
                    if extra.tags is None:
                        concept_service.apply_levels_to_question(question, row_names)
                # After extraction, which writes levels of its own.
                apply_stored_values(question, extra)


def seed():
    rows = load_seed_file()

    embedding_service.preload(
        seed_embeddings.read(seed_embeddings.EMBEDDINGS_FILE, settings.embedding_model)
    )
    try:
        asyncio.run(_seed(rows))
    finally:
        embedding_service.clear_preloaded()


if __name__ == "__main__":
    seed()
