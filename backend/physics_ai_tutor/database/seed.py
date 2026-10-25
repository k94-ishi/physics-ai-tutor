import json
from pathlib import Path

from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionSource,
    QuestionStatus,
)
from physics_ai_tutor.services.question_service import import_questions_from_jsonl


def load_seed_entries(seed_file: Path) -> list[QuestionCreate]:
    """Read seed.json. Entries may use `question`/`answer` (Japanese) or the
    explicit `question_ja`/`answer_ja`/`question_en`/`answer_en` columns;
    missing languages are machine translated on import.
    """
    with open(seed_file, encoding="utf-8") as f:
        data = json.load(f)

    return [QuestionCreate(**entry) for entry in data]


def seed():
    seed_file = Path(__file__).resolve().parent / "seed.json"
    questions = load_seed_entries(seed_file)

    db = SessionLocal()

    try:
        import_questions_from_jsonl(
            db,
            questions,
            status=QuestionStatus.APPROVED,
            source=QuestionSource.MANUAL,
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
