import json
from pathlib import Path

from pydantic import BaseModel, Field

from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionSource,
    QuestionStatus,
)
from physics_ai_tutor.services.question_service import import_questions_from_jsonl


class SeedLevels(BaseModel):
    """Difficulty ratings stored in seed.json so a fresh stack has them ([40])."""

    physics_level: int | None = Field(default=None, ge=0, le=4)
    math_level: int | None = Field(default=None, ge=0, le=4)


LEVEL_KEYS = ("physics_level", "math_level")


def load_seed_file(seed_file: Path) -> list[tuple[QuestionCreate, SeedLevels]]:
    """Read seed.json into question texts plus their optional levels.

    Entries may use `question`/`answer` (Japanese) or the explicit
    `question_ja`/`answer_ja`/`question_en`/`answer_en` columns; missing
    languages are machine translated on import.
    """
    with open(seed_file, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for entry in data:
        levels = {key: entry.pop(key) for key in LEVEL_KEYS if key in entry}
        rows.append((QuestionCreate(**entry), SeedLevels(**levels)))
    return rows


def load_seed_entries(seed_file: Path) -> list[QuestionCreate]:
    return [question for question, _ in load_seed_file(seed_file)]


def apply_seed_levels(questions: list[Question], levels: list[SeedLevels]) -> None:
    # Seeded ratings win over the ones concept extraction just produced.
    for question, seed_levels in zip(questions, levels, strict=True):
        if seed_levels.physics_level is not None:
            question.physics_level = seed_levels.physics_level
        if seed_levels.math_level is not None:
            question.math_level = seed_levels.math_level


def seed():
    seed_file = Path(__file__).resolve().parent / "seed.json"
    rows = load_seed_file(seed_file)

    db = SessionLocal()

    try:
        questions = import_questions_from_jsonl(
            db,
            [question for question, _ in rows],
            status=QuestionStatus.APPROVED,
            source=QuestionSource.MANUAL,
        )
        apply_seed_levels(questions, [levels for _, levels in rows])
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
