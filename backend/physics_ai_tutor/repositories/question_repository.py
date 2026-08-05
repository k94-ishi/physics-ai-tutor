from sqlalchemy.orm import Session

from physics_ai_tutor.models.question import Question
from physics_ai_tutor.schemas.question import QuestionCreate, QuestionUpdate


def get_questions(db: Session) -> list[Question]:
    return db.query(Question).all()


def get_question(db: Session, question_id: int) -> Question:
    return (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )


def create_question(db: Session,
                    question: str,
                    answer: str
                    ):
    db_question = Question(
        question=question,
        answer=answer
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return db_question


def create_questions(
    db: Session,
    questions: list[QuestionCreate],
):
    db_questions = [
        Question(
            question=q.question,
            answer=q.answer,
        )
        for q in questions
    ]

    db.add_all(db_questions)
    db.commit()

    for question in db_questions:
        db.refresh(question)

    return db_questions


def delete(db: Session, question_id: int) -> bool:
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if not question:
        return False

    db.delete(question)
    db.commit()

    return True


def update(
    db: Session,
    question_id: int,
    question_data: QuestionUpdate,
) -> Question | None:
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if not question:
        return None

    question.question = question_data.question
    question.answer = question_data.answer

    db.commit()
    db.refresh(question)

    return question