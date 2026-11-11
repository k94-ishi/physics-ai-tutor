"""Write use cases: create, import, update, delete, save AI answers, concepts."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.core.exceptions import (
    ConceptExtractionError,
    DuplicateQuestionError,
)
from physics_ai_tutor.database.transaction import async_transaction, transaction
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import (
    question_concept_repository,
    question_repository,
)
from physics_ai_tutor.schemas.concept import ConceptExtractionResult
from physics_ai_tutor.schemas.language import Language, TextProvenance
from physics_ai_tutor.schemas.question import (
    GenerationMeta,
    QuestionCreate,
    QuestionSource,
    QuestionStatus,
    QuestionUpdate,
)
from physics_ai_tutor.services import (
    concept_service,
    embedding_service,
)
from physics_ai_tutor.services.question_presentation_service import (
    prepare_for_response,
)
from physics_ai_tutor.services.question_translation_service import (
    async_write_embeddings,
    embed_language,
    refresh_machine_translations,
    translate_missing,
)

logger = logging.getLogger(__name__)


def extract_concepts_best_effort(db: Session, question: Question) -> None:
    """Public entry for callers that import rows without stored tags."""
    attach_concepts_best_effort(db, question)


def attach_concepts_best_effort(db: Session, question: Question) -> None:
    text = question.original_text()
    try:
        names = concept_service.extract_concept_names(
            *text, language=question.original_language
        )
        concept_service.attach_concepts_to_question(
            db, question.id, names, language=question.original_language
        )
        concept_service.apply_levels_to_question(question, names)
    except ConceptExtractionError:
        logger.warning(
            "Concept extraction failed; question saved without concepts: "
            "question_id=%d",
            question.id,
        )


def _check_duplicates(db: Session, texts: dict[Language, tuple[str, str]]) -> None:
    for lang, (q, _) in texts.items():
        if question_repository.get_by_exact_text(db, q, language=lang) is not None:
            raise DuplicateQuestionError(
                f"A question with identical text already exists: {q}"
            )


def create_question(
    db: Session,
    question: QuestionCreate,
    status: str = QuestionStatus.APPROVED,
    source: str = QuestionSource.MANUAL,
    language: Language | str = Language.JA,
):
    texts = question.texts()
    _check_duplicates(db, texts)

    with transaction(db, "create_question"):
        db_question = question_repository.create_question(
            db,
            texts=texts,
            original_language=question.original_language(),
            status=status,
            source=source,
        )

        for lang in texts:
            embed_language(db, db_question, lang)

        if status == QuestionStatus.APPROVED:
            attach_concepts_best_effort(db, db_question)

        translate_missing(db, db_question)
        prepare_for_response(db, [db_question], language)

    logger.info("Question created: id=%d", db_question.id)

    return db_question


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
    extract_concepts: bool = True,
) -> list[Question]:
    """Create rows; `extract_concepts=False` lets the seed supply stored tags."""
    duplicates = _find_duplicate_texts(db, rows)

    if duplicates:
        raise DuplicateQuestionError(
            "Duplicate question text found, nothing was imported: "
            + ", ".join(duplicates)
        )

    with transaction(db, "import_questions_from_jsonl"):
        db_questions = question_repository.create_questions(
            db,
            [(row.texts(), row.original_language()) for row in rows],
            status=status,
            source=source,
        )

        for db_question in db_questions:
            for lang in Language:
                embed_language(db, db_question, lang)

            if extract_concepts and status == QuestionStatus.APPROVED:
                attach_concepts_best_effort(db, db_question)

            translate_missing(db, db_question)

        prepare_for_response(db, db_questions, language)

    logger.info("Questions imported: count=%d", len(db_questions))
    return db_questions


def delete_question(db: Session, question_id: int) -> bool:
    with transaction(db, "delete_question"):
        result = question_repository.delete(db, question_id)

    logger.info("Question delete requested: id=%d found=%s", question_id, result)
    return result


def update_question(
    db: Session,
    question_id: int,
    question_data: QuestionUpdate,
    language: Language | str = Language.JA,
):
    with transaction(db, "update_question"):
        question = question_repository.get_question(db, question_id)

        if question is None:
            return None

        # The teacher's word on difficulty beats the LLM's advisory rating.
        for field, value in question_data.levels().items():
            setattr(question, field, value)

        edited = question_data.texts()

        for lang, (q, a) in edited.items():
            provenance = (
                TextProvenance.ORIGINAL
                if lang == question.original_language
                else TextProvenance.HUMAN
            )
            question.set_text(lang, q, a, provenance)
            db.flush()
            embed_language(db, question, lang)

        # A single-language edit refreshes machine-made counterparts.
        if len(edited) == 1:
            refresh_machine_translations(db, question, next(iter(edited)))

        prepare_for_response(db, [question], language)

    logger.info("Question updated: id=%d", question_id)

    return question


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
            with transaction(db, "reextract_concepts"):
                question_concept_repository.delete_by_question_id(db, question_id)
                names = concept_service.extract_concept_names(
                    *question.original_text(), language=question.original_language
                )
                concepts = concept_service.attach_concepts_to_question(
                    db, question_id, names, language=question.original_language
                )
                concept_service.apply_levels_to_question(question, names)
        except Exception:
            logger.warning(
                "Concept re-extraction failed: question_id=%d",
                question_id,
                exc_info=True,
            )
            results.append(
                ConceptExtractionResult(question_id=question_id, success=False)
            )
            continue

        results.append(
            ConceptExtractionResult(
                question_id=question_id,
                success=True,
                concepts=[c.display_name(question.original_language) for c in concepts],
            )
        )
        logger.info("Concepts re-extracted: question_id=%d", question_id)

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


async def async_save_ai_question(
    db: AsyncSession,
    question: str,
    answer: str,
    language: Language | str = Language.JA,
    source: str = QuestionSource.AI_GENERATED,
    retrieved_question_ids: list[int] | None = None,
    generation: GenerationMeta | None = None,
) -> Question | None:
    """Best-effort save of an AI answer as a new UNREVIEWED question.

    Never raises. Translation into the other language is not done here
    (it would delay the student's response); callers schedule
    `async_translate_missing_languages` afterwards. The sync twin was
    removed in [82]: nothing had called it since [70].

    The embedding call happens before the transaction opens, so no
    connection waits on OpenAI ([82]). A duplicate therefore costs one
    embedding call it did not before - rare (the ask flow already
    checked the cache for this exact text) and cheaper than every save
    holding a connection for the call.
    """
    lang = Language(language)

    try:
        question_vec, answer_vec = await embedding_service.async_create_embeddings(
            [question, answer]
        )

        async with async_transaction(db, "save_ai_question"):
            if await question_repository.async_get_by_exact_text(
                db, question, language=lang
            ):
                logger.info("AI answer not saved: duplicate question text")
                return None

            db_question = await question_repository.async_create_question(
                db,
                texts={lang: (question, answer)},
                original_language=lang,
                status=QuestionStatus.UNREVIEWED,
                source=source,
                retrieved_question_ids=retrieved_question_ids,
            )

            if generation is not None:
                db_question.generation_model = generation.model
                db_question.prompt_version = generation.prompt_version
                db_question.generation_mode = generation.mode
                db_question.prompt_tokens = generation.prompt_tokens
                db_question.completion_tokens = generation.completion_tokens
                await db.flush()

            await async_write_embeddings(
                db, db_question.id, lang, question_vec, answer_vec
            )
    except Exception:
        # The student already has the answer; saving it is best effort.
        logger.warning(
            "Failed to save AI answer as question; continuing without saving",
            exc_info=True,
        )
        return None

    logger.info("AI answer saved as question: id=%d", db_question.id)
    return db_question
