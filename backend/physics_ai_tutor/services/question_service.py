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
    question_concept_repository,
    question_repository,
    question_review_repository,
)
from physics_ai_tutor.schemas.concept import ConceptExtractionResult
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


def attach_concept_names(db: Session, questions: list[Question]) -> None:
    """Populate each question's transient `.concepts` attribute (list[str]).

    Not a mapped column - `QuestionResponse.model_config = {"from_attributes":
    True}` reads it via getattr, so this only needs to run before a Question
    is serialized as a response, regardless of whether it was just committed
    or only flushed within the current transaction.
    """
    if not questions:
        return

    concepts_by_id = question_concept_repository.get_concepts_for_questions(
        db, [q.id for q in questions]
    )

    for question in questions:
        question.concepts = concepts_by_id.get(question.id, [])


def attach_retrieved_questions(db: Session, questions: list[Question]) -> None:
    """Populate each question's transient `.retrieved_questions` attribute
    (list[dict]) by resolving `retrieved_question_ids` to lightweight
    {id, question} summaries, so RAG result cards can show what they were
    generated from without a per-card frontend fetch. Same pattern as
    `attach_concept_names` - must run before every QuestionResponse
    serialization since the attribute is transient, not a mapped column.
    """
    if not questions:
        return

    all_ids = {
        question_id
        for question in questions
        for question_id in question.retrieved_question_ids
    }

    if not all_ids:
        for question in questions:
            question.retrieved_questions = []
        return

    referenced_by_id = {
        referenced.id: referenced
        for referenced in question_repository.get_questions_by_ids(db, list(all_ids))
    }

    for question in questions:
        question.retrieved_questions = [
            {"id": referenced_id, "question": referenced_by_id[referenced_id].question}
            for referenced_id in question.retrieved_question_ids
            if referenced_id in referenced_by_id
        ]


def fetch_questions(
    db: Session,
    page: int,
    size: int,
    keyword: str | None = None,
    status: str | None = None,
    exclude_status: str | None = None,
    search_question: bool = True,
    search_answer: bool = True,
) -> QuestionListResponse:

    offset = (page - 1) * size

    questions = question_repository.get_questions(
        db,
        offset=offset,
        limit=size,
        keyword=keyword,
        status=status,
        exclude_status=exclude_status,
        search_question=search_question,
        search_answer=search_answer,
    )

    total = question_repository.count_questions(
        db,
        keyword=keyword,
        status=status,
        exclude_status=exclude_status,
        search_question=search_question,
        search_answer=search_answer,
    )

    attach_concept_names(db, questions)
    attach_retrieved_questions(db, questions)

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
    question = question_repository.get_question(
        db,
        question_id,
        exclude_status=exclude_status,
    )

    if question is not None:
        attach_concept_names(db, [question])
        attach_retrieved_questions(db, [question])

    return question


def fetch_question_by_exact_text(
    db: Session,
    question_text: str,
    exclude_status: str | None = None,
) -> Question | None:
    question = question_repository.get_by_exact_text(
        db,
        question_text,
        exclude_status=exclude_status,
    )

    if question is not None:
        attach_concept_names(db, [question])
        attach_retrieved_questions(db, [question])

    return question


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
        # -> Extract concepts (only if becoming APPROVED, best effort) -> Commit
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

        if status == QuestionStatus.APPROVED:
            _attach_concepts_best_effort(
                db, db_question.id, question.question, question.answer
            )

        attach_concept_names(db, [db_question])
        attach_retrieved_questions(db, [db_question])

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

            if status == QuestionStatus.APPROVED:
                for q in db_questions:
                    _attach_concepts_best_effort(db, q.id, q.question, q.answer)

            attach_concept_names(db, db_questions)
            attach_retrieved_questions(db, db_questions)

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

        attach_concept_names(db, [question])
        attach_retrieved_questions(db, [question])

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

        # Concept extraction is triggered by the status becoming APPROVED
        # (via APPROVE or EDIT_APPROVE), not by question creation.
        if new_status == QuestionStatus.APPROVED:
            _attach_concepts_best_effort(
                db, question_id, updated.question, updated.answer
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

        attach_concept_names(db, [updated])
        attach_retrieved_questions(db, [updated])

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


def reextract_concepts_for_questions(
    db: Session, question_ids: list[int]
) -> list[ConceptExtractionResult]:
    """Re-run concept extraction for the given questions, regardless of
    their current status or whether they already have concepts attached.

    Each question is processed and committed independently so that one
    failure (e.g. DeepSeek being down) doesn't roll back successes for
    the rest of the batch - this is the manual recovery path for
    concept-extraction failures.
    """
    results = []

    for question_id in question_ids:
        question = question_repository.get_question(db, question_id)

        if question is None:
            results.append(
                ConceptExtractionResult(question_id=question_id, success=False)
            )
            continue

        try:
            question_concept_repository.delete_by_question_id(db, question_id)
            concept_names = concept_service.extract_concept_names(
                question.question, question.answer
            )
            concept_service.attach_concepts_to_question(
                db, question_id, concept_names
            )
            db.commit()

            results.append(
                ConceptExtractionResult(
                    question_id=question_id, success=True, concepts=concept_names
                )
            )
            logger.info("Concepts re-extracted: question_id=%d", question_id)
        except Exception:
            logger.warning(
                "Concept re-extraction failed: question_id=%d",
                question_id,
                exc_info=True,
            )
            db.rollback()
            results.append(
                ConceptExtractionResult(question_id=question_id, success=False)
            )

    return results


def bulk_delete_questions(
    db: Session, question_ids: list[int]
) -> tuple[int, list[int]]:
    deleted_count = 0
    not_found_ids: list[int] = []

    for question_id in question_ids:
        if delete_question(db, question_id):
            deleted_count += 1
        else:
            not_found_ids.append(question_id)

    return deleted_count, not_found_ids


def bulk_review_questions(
    db: Session,
    question_ids: list[int],
    action: QuestionReviewAction,
    reviewer_id: int,
    comment: str | None = None,
) -> tuple[list[Question], list[int]]:
    updated_questions: list[Question] = []
    not_found_ids: list[int] = []

    for question_id in question_ids:
        result = review_question(
            db, question_id, action=action, reviewer_id=reviewer_id, comment=comment
        )

        if result is None:
            not_found_ids.append(question_id)
        else:
            updated_questions.append(result)

    return updated_questions, not_found_ids


def save_ai_question(
    db: Session,
    question: str,
    answer: str,
    source: str = QuestionSource.AI_GENERATED,
    retrieved_question_ids: list[int] | None = None,
) -> Question | None:
    """Best-effort save of a direct AI (or RAG) answer as a new question.

    Never raises: any failure (duplicate text, embedding generation, DB
    error) is logged and swallowed so the caller can always still return
    the DeepSeek answer to the user regardless of whether it was saved.
    No concept extraction here - saved questions start as UNREVIEWED, and
    concept extraction is only triggered once a question is APPROVED.
    """
    try:
        if question_repository.get_by_exact_text(db, question) is not None:
            logger.info("AI answer not saved: duplicate question text")
            return None

        db_question = question_repository.create_question(
            db,
            question=question,
            answer=answer,
            status=QuestionStatus.UNREVIEWED,
            source=source,
            retrieved_question_ids=retrieved_question_ids,
        )

        texts = [question, answer]
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

        logger.info("AI answer saved as question: id=%d", db_question.id)

        return db_question
    except Exception:
        logger.warning(
            "Failed to save AI answer as question; continuing without saving",
            exc_info=True,
        )
        db.rollback()
        return None
