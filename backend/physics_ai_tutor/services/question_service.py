import logging

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

logger = logging.getLogger(__name__)


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

        logger.info("Question created: id=%d", db_question.id)

        return db_question

    except Exception:
        logger.warning("Rolling back transaction: operation=create_question")
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

        if db_questions:
            texts = [q.question for q in db_questions]
            texts.extend(q.answer for q in db_questions)

            vectors = embedding_service.create_embeddings(texts)
            embedding_records = []
            question_count = len(db_questions)

            for i, q in enumerate(db_questions):
                embedding_records.append(
                    {
                        "question_id": q.id,
                        "type": "question",
                        "embedding": vectors[i],
                        "model": settings.embedding_model,
                    }
                )

                embedding_records.append(
                    {
                        "question_id": q.id,
                        "type": "answer",
                        "embedding": vectors[question_count  + i],
                        "model": settings.embedding_model,
                    }
                )

            embedding_repository.create_embeddings(
                db,
                embedding_records,
            )

        db.commit()

        logger.info("Questions created: count=%d", len(db_questions))
    except Exception:
        logger.warning("Rolling back transaction: operation=create_questions")
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

        logger.info("Question delete requested: id=%d found=%s", question_id, result)
    except Exception:
        logger.warning("Rolling back transaction: operation=delete_question")
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
        
        if question is None:
            return None
        
        texts = [
            question_data.question,
            question_data.answer,
        ]
        question_vec, answer_vec = embedding_service.create_embeddings(texts)
        embedding_repository.delete_by_question_id(db, question_id)
        
        embedding_repository.create_embedding(
            db,
            question_id=question_id,
            embedding=question_vec,
            embedding_type="question",
            model=settings.embedding_model,
        )

        embedding_repository.create_embedding(
            db,
            question_id=question_id,
            embedding=answer_vec,
            embedding_type="answer",
            model=settings.embedding_model,
        )
        
        db.commit()

        logger.info("Question updated: id=%d", question_id)

        return question
    except Exception:
        logger.warning("Rolling back transaction: operation=update_question")
        db.rollback()
        raise