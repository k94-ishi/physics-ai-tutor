from sqlalchemy.orm import Session

from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import question_repository


def fetch_questions(db: Session) -> list[Question]:
    return question_repository.get_questions(db)