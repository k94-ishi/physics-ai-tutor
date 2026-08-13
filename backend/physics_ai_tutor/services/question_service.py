import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import (
    ConceptExtractionError,
    DuplicateQuestionError,
)
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import (
    embedding_repository,
    question_repository,
    question_review_repository,
)
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionListResponse,
    QuestionSource,
    QuestionStatus,
    QuestionUpdate,
)
from physics_ai_tutor.schemas.question_review import QuestionReviewAction
from physics_ai_tutor.services import concept_service, embedding_service

logger = logging.getLogger(__name__)


def fetch_questions(
    db: Session,
    page: int,
    size: int,
    keyword: str | None = None,
    status: str | None = None,
    exclude_status: str | None = None,
) -> QuestionListResponse:

    offset = (page - 1) * size

    questions = question_repository.get_questions(
        db,
        offset=offset,
        limit=size,
        keyword=keyword,
        status=status,
        exclude_status=exclude_status,
    )

    total = question_repository.count_questions(
        db, keyword=keyword, status=status, exclude_status=exclude_status
    )

    logger.info(
        "Questions fetched: page=%d size=%d keyword_present=%s results=%d total=%d",
        page,
        size,
        keyword is not None,
        len(questions),
        total,
    )

    return QuestionListResponse(
        items=questions,
        total=total,
        page=page,
        size=size,
    )


def fetch_question(
    db: Session,
    question_id: int,
    exclude_status: str | None = None,
) -> Question:
    return question_repository.get_question(
        db,
        question_id,
        exclude_status=exclude_status,
    )


def _attach_concepts_best_effort(
    db: Session, question_id: int, question: str, answer: str
) -> None:
    try:
        concept_names = concept_service.extract_concept_names(question, answer)
        concept_service.attach_concepts_to_question(db, question_id, concept_names)
    except ConceptExtractionError:
        logger.warning(
            "Concept extraction failed; question saved without concepts: "
            "question_id=%d",
            question_id,
        )


def create_question(
    db: Session,
    question: QuestionCreate,
    status: str = QuestionStatus.APPROVED,
    source: str = QuestionSource.MANUAL,
):
    if question_repository.get_by_exact_text(db, question.question) is not None:
        raise DuplicateQuestionError(
            f"A question with identical text already exists: {question.question}"
        )

    try:
        # Save question -> Create embeddings
        # -> Save question emedding -> Save answer embedding
        # -> Extract concepts (best effort) -> Commit
        db_question = question_repository.create_question(
            db,
            question=question.question,
            answer=question.answer,
            status=status,
            source=source,
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

        _attach_concepts_best_effort(
            db, db_question.id, question.question, question.answer
        )

        db.commit()

        logger.info("Question created: id=%d", db_question.id)

        return db_question

    except Exception:
        logger.warning("Rolling back transaction: operation=create_question")
        db.rollback()
        raise


def _find_duplicate_texts(db: Session, rows: list[QuestionCreate]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []

    for row in rows:
        if row.question in seen:
            duplicates.append(row.question)
            continue

        seen.add(row.question)

        if question_repository.get_by_exact_text(db, row.question) is not None:
            duplicates.append(row.question)

    return duplicates


def import_questions_from_jsonl(
    db: Session,
    rows: list[QuestionCreate],
    status: str,
    source: str,
) -> list[Question]:
    duplicates = _find_duplicate_texts(db, rows)

    if duplicates:
        raise DuplicateQuestionError(
            "Duplicate question text found, nothing was imported: "
            + ", ".join(duplicates)
        )

    try:
        db_questions = question_repository.create_questions(
            db,
            rows,
            status=status,
            source=source,
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
                        "embedding": vectors[question_count + i],
                        "model": settings.embedding_model,
                    }
                )

            embedding_repository.create_embeddings(
                db,
                embedding_records,
            )

            for q in db_questions:
                _attach_concepts_best_effort(db, q.id, q.question, q.answer)

        db.commit()

        logger.info("Questions imported: count=%d", len(db_questions))
    except Exception:
        logger.warning(
            "Rolling back transaction: operation=import_questions_from_jsonl"
        )
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


def review_question(
    db: Session,
    question_id: int,
    action: QuestionReviewAction,
    reviewer_id: int,
    question: str | None = None,
    answer: str | None = None,
    comment: str | None = None,
) -> Question | None:
    try:
        current = question_repository.get_question(db, question_id)

        if current is None:
            return None

        before_question = current.question
        before_answer = current.answer

        if action == QuestionReviewAction.EDIT_APPROVE:
            new_status = QuestionStatus.APPROVED
            new_question = question
            new_answer = answer
        elif action == QuestionReviewAction.APPROVE:
            new_status = QuestionStatus.APPROVED
            new_question = None
            new_answer = None
        else:
            new_status = QuestionStatus.REJECTED
            new_question = None
            new_answer = None

        updated = question_repository.update_content_and_status(
            db,
            question_id,
            status=new_status,
            question=new_question,
            answer=new_answer,
        )

        if action == QuestionReviewAction.EDIT_APPROVE:
            texts = [updated.question, updated.answer]
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

        question_review_repository.create(
            db,
            question_id=question_id,
            action=action,
            reviewer_id=reviewer_id,
            before_question=before_question,
            before_answer=before_answer,
            after_question=updated.question,
            after_answer=updated.answer,
            comment=comment,
        )

        db.commit()

        logger.info(
            "Question reviewed: id=%d action=%s reviewer_id=%d",
            question_id, action, reviewer_id,
        )

        return updated
    except Exception:
        logger.warning("Rolling back transaction: operation=review_question")
        db.rollback()
        raise


def fetch_question_reviews(db: Session, question_id: int):
    return question_review_repository.list_for_question(db, question_id)
