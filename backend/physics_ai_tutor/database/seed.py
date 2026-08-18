import json
from pathlib import Path

from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionSource,
    QuestionStatus,
)
from physics_ai_tutor.services.question_service import import_questions_from_jsonl


def seed():
    BASE_DIR = Path(__file__).resolve().parent
    seed_file = BASE_DIR / "seed.json"
    with open(seed_file, encoding="utf-8") as f:
        data = json.load(f)

    questions = [
        QuestionCreate(
            question=d["question"],
            answer=d["answer"],
        )
        for d in data
    ]

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
