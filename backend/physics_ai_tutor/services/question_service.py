from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import embedding_repository, question_repository
from physics_ai_tutor.schemas.question import (
    QuestionBulkCreate,
    QuestionCreate,
    QuestionUpdate,
)
from physics_ai_tutor.services import embedding_service


def fetch_questions(db: Session) -> list[Question]:
    return question_repository.get_questions(db)


def fetch_question(db: Session, question_id: int) -> Question:
    return question_repository.get_question(
        db,
        question_id,
    )


def create_question(db: Session, question: QuestionCreate):
    try:
        # Save question -> Create embeddings
        # -> Save question emedding -> Save answer embedding -> Commit
        db_question = question_repository.create_question(
            db,
            question=question.question,
            answer=question.answer
        )
        
        texts = [question.question, question.answer]
        question_vec, answer_vec = embedding_service.create_embeddings(texts)
        
        embedding_repository.create_embedding(
            db,
            question_id=db_question.id,
            embedding=question_vec,
            embedding_type="question",
            model=settings.embedding_model,
        )
        
        embedding_repository.create_embedding(
            db,
            question_id=db_question.id,
            embedding=answer_vec,
            embedding_type="answer",
            model=settings.embedding_model,
        )
         
        db.commit()
        
        return db_question
        
    except Exception:
        db.rollback()
        raise


def create_questions(
    db: Session,
    questions: QuestionBulkCreate,
):
    try:
        db_questions = question_repository.create_questions(
            db,
            questions.questions,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return db_questions


def delete_question(db: Session, question_id: int) -> bool:
    try:
        result = question_repository.delete(
            db,
            question_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return result


def update_question(
    db: Session,
    question_id: int,
    question_data: QuestionUpdate,
):
    try:
        question = question_repository.update(
            db,
            question_id,
            question_data,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    if question is None:
        return None

    return question