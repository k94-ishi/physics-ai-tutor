from sqlalchemy.orm import Session

from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import question_repository
from physics_ai_tutor.schemas.question import (
    QuestionBulkCreate,
    QuestionCreate,
)


def fetch_questions(db: Session) -> list[Question]:
    return question_repository.get_questions(db)


def fetch_question(db: Session, question_id: int) -> Question:
    return question_repository.get_question(
        db,
        question_id,
    )


def create_question(db: Session, question: QuestionCreate):
    return question_repository.create_question(
        db,
        question=question.question,
        answer=question.answer
    )


def create_questions(
    db: Session,
    questions: QuestionBulkCreate,
):
    return question_repository.create_questions(
        db,
        questions.questions,
    )


def delete_question(
    db: Session,
    question_id: int
):
    deleted = question_repository.delete(
        db,
        question_id,
    )

    if not deleted:
        raise ValueError("Question not found")

    return