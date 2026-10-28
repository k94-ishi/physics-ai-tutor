import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import (
    ConceptExtractionError,
    DuplicateQuestionError,
    EmbeddingGenerationError,
    TranslationError,
)
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import (
    embedding_repository,
    question_concept_repository,
    question_repository,
    question_review_repository,
)
from physics_ai_tutor.schemas.concept import ConceptExtractionResult
from physics_ai_tutor.schemas.language import Language, TextProvenance
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionListResponse,
    QuestionSource,
    QuestionStatus,
    QuestionUpdate,
)
from physics_ai_tutor.schemas.question_review import QuestionReviewAction
from physics_ai_tutor.services import (
    concept_service,
    embedding_service,
    translation_service,
)

logger = logging.getLogger(__name__)


# --- response preparation ---------------------------------------------------


def resolve_language(questions: list[Question], language: Language | str) -> None:
    """Populate transient `.question`, `.answer`, `.language`, `.provenance`
    with the text in `language`, falling back to the original language.
    """
    for question in questions:
        question.resolve(language)


def attach_concept_names(
    db: Session, questions: list[Question], language: Language | str = Language.JA
) -> None:
    """Populate each question's transient `.concepts` (display names)."""
    if not questions:
        return

    concepts_by_id = question_concept_repository.get_concepts_for_questions(
        db, [q.id for q in questions], language=Language(language).value
    )

    for question in questions:
        question.concepts = concepts_by_id.get(question.id, [])


def attach_retrieved_questions(
    db: Session, questions: list[Question], language: Language | str = Language.JA
) -> None:
    """Resolve `retrieved_question_ids` to {id, question} summaries."""
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

    referenced = question_repository.get_questions_by_ids(db, list(all_ids))
    resolve_language(referenced, language)
    referenced_by_id = {item.id: item for item in referenced}

    for question in questions:
        question.retrieved_questions = [
            {"id": ref_id, "question": referenced_by_id[ref_id].question}
            for ref_id in question.retrieved_question_ids
            if ref_id in referenced_by_id
        ]


def prepare_for_response(
    db: Session, questions: list[Question], language: Language | str = Language.JA
) -> None:
    resolve_language(questions, language)
    attach_concept_names(db, questions, language)
    attach_retrieved_questions(db, questions, language)


# --- reads --------------------------------------------------------------------


def fetch_questions(
    db: Session,
    page: int,
    size: int,
    keyword: str | None = None,
    status: str | None = None,
    exclude_statuses: list[str] | None = None,
    search_question: bool = True,
    search_answer: bool = True,
    language: Language | str = Language.JA,
    only_with_language: bool = False,
) -> QuestionListResponse:
    offset = (page - 1) * size
    language_filter = Language(language) if only_with_language else None

    questions = question_repository.get_questions(
        db,
        offset=offset,
        limit=size,
        keyword=keyword,
        status=status,
        exclude_statuses=exclude_statuses,
        search_question=search_question,
        search_answer=search_answer,
        language=language_filter,
    )

    total = question_repository.count_questions(
        db,
        keyword=keyword,
        status=status,
        exclude_statuses=exclude_statuses,
        search_question=search_question,
        search_answer=search_answer,
        language=language_filter,
    )

    prepare_for_response(db, questions, language)

    logger.info(
        "Questions fetched: page=%d size=%d keyword_present=%s results=%d total=%d",
        page,
        size,
        keyword is not None,
        len(questions),
        total,
    )

    return QuestionListResponse(items=questions, total=total, page=page, size=size)


def fetch_question(
    db: Session,
    question_id: int,
    exclude_statuses: list[str] | None = None,
    language: Language | str = Language.JA,
    translate_if_missing: bool = False,
) -> Question | None:
    question = question_repository.get_question(
        db, question_id, exclude_statuses=exclude_statuses
    )

    if question is None:
        return None

    # Lazy fill for rows approved before translation existed.
    if translate_if_missing and not question.has(language):
        _translate_into(db, question, Language(language))
        db.commit()

    prepare_for_response(db, [question], language)

    return question


def fetch_question_by_exact_text(
    db: Session,
    question_text: str,
    exclude_statuses: list[str] | None = None,
    language: Language | str = Language.JA,
) -> Question | None:
    question = question_repository.get_by_exact_text(
        db, question_text, language=language, exclude_statuses=exclude_statuses
    )

    if question is not None:
        prepare_for_response(db, [question], language)

    return question


def find_cached_answer(
    db: Session, question_text: str, language: Language | str
) -> Question | None:
    """Cache lookup for the ask flow: any non-rejected row with this exact
    question text in `language`, including unreviewed AI answers.
    """
    return question_repository.get_by_exact_text(
        db,
        question_text,
        language=language,
        exclude_statuses=[QuestionStatus.REJECTED],
    )


# --- internals ----------------------------------------------------------------


def _embed_language(db: Session, question: Question, language: Language) -> None:
    text = question.text(language)
    if text is None:
        return

    question_vec, answer_vec = embedding_service.create_embeddings(list(text))
    embedding_repository.delete_by_question_id(db, question.id, language=language)

    for embedding_type, vector in (("question", question_vec), ("answer", answer_vec)):
        embedding_repository.create_embedding(
            db,
            question_id=question.id,
            embedding=vector,
            embedding_type=embedding_type,
            model=settings.embedding_model,
            language=language.value,
        )


def _attach_concepts_best_effort(db: Session, question: Question) -> None:
    text = question.original_text()
    try:
        names = concept_service.extract_concept_names(
            *text, language=question.original_language
        )
        concept_service.attach_concepts_to_question(
            db, question.id, names, language=question.original_language
        )
    except ConceptExtractionError:
        logger.warning(
            "Concept extraction failed; question saved without concepts: "
            "question_id=%d",
            question.id,
        )


def _translate_into(
    db: Session, question: Question, target: Language, source: Language | None = None
) -> bool:
    """Fill `target` text by machine translation. Best effort; returns success."""
    src = source or Language(question.original_language)
    text = question.text(src)
    if text is None:
        src = Language(question.original_language)
        text = question.original_text()

    try:
        translated_q, translated_a = translation_service.translate_qa(
            text[0], text[1], source=src, target=target
        )
        question.set_text(target, translated_q, translated_a, TextProvenance.MACHINE)
        db.flush()
        _embed_language(db, question, target)
    except (TranslationError, EmbeddingGenerationError):
        logger.warning(
            "Translation skipped: question_id=%d target=%s",
            question.id,
            target,
            exc_info=True,
        )
        return False

    logger.info("Question translated: question_id=%d target=%s", question.id, target)
    return True


def _translate_missing(db: Session, question: Question) -> list[Language]:
    filled = [
        lang
        for lang in Language
        if not question.has(lang) and _translate_into(db, question, lang)
    ]
    return filled


def _refresh_machine_translations(
    db: Session, question: Question, edited: Language
) -> None:
    """After a human edit in `edited`, regenerate machine-made counterparts."""
    for lang in Language:
        if lang == edited:
            continue
        if question.provenance_of(lang) == TextProvenance.MACHINE or not question.has(
            lang
        ):
            _translate_into(db, question, lang, source=edited)


def _check_duplicates(db: Session, texts: dict[Language, tuple[str, str]]) -> None:
    for lang, (q, _) in texts.items():
        if question_repository.get_by_exact_text(db, q, language=lang) is not None:
            raise DuplicateQuestionError(
                f"A question with identical text already exists: {q}"
            )


# --- writes -------------------------------------------------------------------


def create_question(
    db: Session,
    question: QuestionCreate,
    status: str = QuestionStatus.APPROVED,
    source: str = QuestionSource.MANUAL,
    language: Language | str = Language.JA,
):
    texts = question.texts()
    _check_duplicates(db, texts)

    try:
        db_question = question_repository.create_question(
            db,
            texts=texts,
            original_language=question.original_language(),
            status=status,
            source=source,
        )

        for lang in texts:
            _embed_language(db, db_question, lang)

        if status == QuestionStatus.APPROVED:
            _attach_concepts_best_effort(db, db_question)

        _translate_missing(db, db_question)
        prepare_for_response(db, [db_question], language)

        db.commit()

        logger.info("Question created: id=%d", db_question.id)

        return db_question
    except Exception:
        logger.warning("Rolling back transaction: operation=create_question")
        db.rollback()
        raise


def _find_duplicate_texts(db: Session, rows: list[QuestionCreate]) -> list[str]:
    seen: set[tuple[Language, str]] = set()
    duplicates: list[str] = []

    for row in rows:
        for lang, (q, _) in row.texts().items():
            if (lang, q) in seen:
                duplicates.append(q)
                continue
            seen.add((lang, q))
            if question_repository.get_by_exact_text(db, q, language=lang):
                duplicates.append(q)

    return duplicates


def import_questions_from_jsonl(
    db: Session,
    rows: list[QuestionCreate],
    status: str,
    source: str,
    language: Language | str = Language.JA,
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
            [(row.texts(), row.original_language()) for row in rows],
            status=status,
            source=source,
        )

        for db_question in db_questions:
            for lang in Language:
                _embed_language(db, db_question, lang)

            if status == QuestionStatus.APPROVED:
                _attach_concepts_best_effort(db, db_question)

            _translate_missing(db, db_question)

        prepare_for_response(db, db_questions, language)

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
        result = question_repository.delete(db, question_id)
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
    language: Language | str = Language.JA,
):
    try:
        question = question_repository.get_question(db, question_id)

        if question is None:
            return None

        edited = question_data.texts()

        for lang, (q, a) in edited.items():
            provenance = (
                TextProvenance.ORIGINAL
                if lang == question.original_language
                else TextProvenance.HUMAN
            )
            question.set_text(lang, q, a, provenance)
            db.flush()
            _embed_language(db, question, lang)

        # A single-language edit refreshes machine-made counterparts.
        if len(edited) == 1:
            _refresh_machine_translations(db, question, next(iter(edited)))

        prepare_for_response(db, [question], language)

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
    reason: str | None = None,
    comment: str | None = None,
    language: Language | str | None = None,
    response_language: Language | str = Language.JA,
) -> Question | None:
    try:
        current = question_repository.get_question(db, question_id)

        if current is None:
            return None

        lang = Language(language) if language else Language(current.original_language)
        before = current.text(lang) or current.original_text()

        if action == QuestionReviewAction.REJECT:
            new_status = QuestionStatus.REJECTED
        else:
            new_status = QuestionStatus.APPROVED

        if action == QuestionReviewAction.EDIT_APPROVE:
            assert question is not None and answer is not None
            provenance = (
                TextProvenance.ORIGINAL
                if lang == current.original_language
                else TextProvenance.HUMAN
            )
            current.set_text(lang, question, answer, provenance)
            db.flush()
            _embed_language(db, current, lang)
            _refresh_machine_translations(db, current, lang)

        question_repository.update_status(db, question_id, new_status)

        # Concept extraction is triggered by the status becoming APPROVED.
        if new_status == QuestionStatus.APPROVED:
            _attach_concepts_best_effort(db, current)
            _translate_missing(db, current)

        after = current.text(lang) or current.original_text()

        question_review_repository.create(
            db,
            question_id=question_id,
            action=action,
            reviewer_id=reviewer_id,
            language=lang.value,
            reason=reason,
            before_question=before[0],
            before_answer=before[1],
            after_question=after[0],
            after_answer=after[1],
            comment=comment,
        )

        prepare_for_response(db, [current], response_language)

        db.commit()

        logger.info(
            "Question reviewed: id=%d action=%s reviewer_id=%d language=%s",
            question_id,
            action,
            reviewer_id,
            lang,
        )

        return current
    except Exception:
        logger.warning("Rolling back transaction: operation=review_question")
        db.rollback()
        raise


def fetch_question_reviews(db: Session, question_id: int):
    return question_review_repository.list_for_question(db, question_id)


def reextract_concepts_for_questions(
    db: Session, question_ids: list[int]
) -> list[ConceptExtractionResult]:
    """Re-run concept extraction; each question commits independently."""
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
            names = concept_service.extract_concept_names(
                *question.original_text(), language=question.original_language
            )
            concepts = concept_service.attach_concepts_to_question(
                db, question_id, names, language=question.original_language
            )
            db.commit()

            results.append(
                ConceptExtractionResult(
                    question_id=question_id,
                    success=True,
                    concepts=[
                        c.display_name(question.original_language) for c in concepts
                    ],
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


def translate_missing_languages(db: Session, question_id: int) -> list[Language]:
    """Fill every missing language of one question; commits on its own.

    Used by the background task after an AI answer, the admin endpoint, and
    the backfill CLI.
    """
    question = question_repository.get_question(db, question_id)

    if question is None:
        return []

    try:
        filled = _translate_missing(db, question)
        db.commit()
    except Exception:
        logger.warning("Rolling back transaction: operation=translate_missing")
        db.rollback()
        raise

    return filled


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
    reason: str | None = None,
    comment: str | None = None,
    response_language: Language | str = Language.JA,
) -> tuple[list[Question], list[int]]:
    updated_questions: list[Question] = []
    not_found_ids: list[int] = []

    for question_id in question_ids:
        result = review_question(
            db,
            question_id,
            action=action,
            reviewer_id=reviewer_id,
            reason=reason,
            comment=comment,
            response_language=response_language,
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
    language: Language | str = Language.JA,
    source: str = QuestionSource.AI_GENERATED,
    retrieved_question_ids: list[int] | None = None,
) -> Question | None:
    """Best-effort save of an AI answer as a new UNREVIEWED question.

    Never raises. Translation into the other language is not done here (it
    would delay the student's response); callers schedule
    `translate_missing_languages` afterwards.
    """
    lang = Language(language)

    try:
        if question_repository.get_by_exact_text(db, question, language=lang):
            logger.info("AI answer not saved: duplicate question text")
            return None

        db_question = question_repository.create_question(
            db,
            texts={lang: (question, answer)},
            original_language=lang,
            status=QuestionStatus.UNREVIEWED,
            source=source,
            retrieved_question_ids=retrieved_question_ids,
        )

        _embed_language(db, db_question, lang)

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
