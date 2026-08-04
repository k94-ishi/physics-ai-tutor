from sqlalchemy.orm import Session

from physics_ai_tutor.models.question import Question


def get_questions(db: Session) -> list[Question]:
    return db.query(Question).all()