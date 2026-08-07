import json
from pathlib import Path

from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.models.question import Question


def seed():
    BASE_DIR = Path(__file__).resolve().parent
    seed_file = BASE_DIR / "seed.json"
    with open(seed_file, encoding="utf-8") as f:
        data = json.load(f)
    
    questions = [
        Question(
            question=d["question"],
            answer=d["answer"],
        ) for d in data
    ]
    
    db = SessionLocal()

    try:
        db.add_all(questions)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()