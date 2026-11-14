"""Write use cases: create, import, update, delete, save AI answers, concepts."""

import logging
from dataclasses import dataclass, field

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
    async_prepare_for_response,
    prepare_for_response,
)
from physics_ai_tutor.services.question_translation_service import (
    PreparedTranslation,
    async_apply_translation,
    async_prepare_refresh,
    async_prepare_translation,
    async_write_embeddings,
    draft_of,
    embed_language,
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


async def _check_duplicates(
    db: AsyncSession, texts: dict[Language, tuple[str, str]]
) -> None:
    for lang, (q, _) in texts.items():
        if await question_repository.async_get_by_exact_text(db, q, language=lang):
            raise DuplicateQuestionError(
                f"A question with identical text already exists: {q}"
            )


@dataclass
class _PreparedCreate:
    """The AI results for a new row, computed before anything is written."""

    vectors: dict[Language, tuple[list[float], list[float]]]
    translations: dict[Language, PreparedTranslation] = field(default_factory=dict)
    concept_names: list[str] | None = None
    concept_plans: list[concept_service.PlannedSense] = field(default_factory=list)


async def _prepare_create(
    db: AsyncSession, draft: Question, approved: bool
) -> _PreparedCreate:
    """Embeddings, concepts and translations, with no transaction open ([82])."""
    vectors = {}
    for lang in Language:
        text = draft.text(lang)
        if text is not None:
            # An embedding failure aborts the create, as it always has.
            q_vec, a_vec = await embedding_service.async_create_embeddings(list(text))
            vectors[lang] = (q_vec, a_vec)
    prepared = _PreparedCreate(vectors=vectors)
    if approved:
        await _prepare_concepts(db, draft, prepared)
    for lang in Language:
        if not draft.has(lang):
            translation = await async_prepare_translation(draft, lang)
            if translation is not None:
                prepared.translations[lang] = translation
    return prepared


async def _prepare_concepts(
    db: AsyncSession, draft: Question, prepared: _PreparedCreate
) -> None:
    language = draft.original_language
    try:
        names = await concept_service.async_extract_concept_names(
            *draft.original_text(), language=language
        )
    except ConceptExtractionError:
        logger.warning("Concept extraction failed; question saved without concepts")
        return
    prepared.concept_names = names
    prepared.concept_plans = await concept_service.async_prepare_concepts(
        db, names, language
    )


async def create_question(
    db: AsyncSession,
    question: QuestionCreate,
    status: str = QuestionStatus.APPROVED,
    source: str = QuestionSource.MANUAL,
    language: Language | str = Language.JA,
):
    """Read, prepare with no transaction, then one short write ([93])."""
    texts = question.texts()
    async with async_transaction(db, "create_question_read"):
        await _check_duplicates(db, texts)

    draft = question_repository.build_question(
        texts, question.original_language(), status, source
    )
    prepared = await _prepare_create(db, draft, status == QuestionStatus.APPROVED)

    async with async_transaction(db, "create_question"):
        db.add(draft)
        await db.flush()
        for lang, (q_vec, a_vec) in prepared.vectors.items():
            await async_write_embeddings(db, draft.id, lang, q_vec, a_vec)
        for target, translation in prepared.translations.items():
            await async_apply_translation(db, draft, target, translation)
        if prepared.concept_names is not None:
            await concept_service.async_apply_concepts(
                db, draft.id, prepared.concept_plans
            )
            concept_service.apply_levels_to_question(draft, prepared.concept_names)
        await async_prepare_for_response(db, [draft], language)

    logger.info("Question created: id=%d", draft.id)

    return draft


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


async def delete_question(db: AsyncSession, question_id: int) -> bool:
    async with async_transaction(db, "delete_question"):
        result = await question_repository.delete(db, question_id)

    logger.info("Question delete requested: id=%d found=%s", question_id, result)
    return result


def _edit_provenance(question: Question, lang: Language) -> str:
    return (
        TextProvenance.ORIGINAL
        if lang == question.original_language
        else TextProvenance.HUMAN
    )


async def update_question(
    db: AsyncSession,
    question_id: int,
    question_data: QuestionUpdate,
    language: Language | str = Language.JA,
):
    """Read, prepare on a draft with no transaction, then one short write ([93])."""
    async with async_transaction(db, "update_question_read"):
        question = await question_repository.async_get_question(db, question_id)
    if question is None:
        return None

    edited = question_data.texts()
    draft = draft_of(question)
    vectors = {}
    for lang, (q, a) in edited.items():
        draft.set_text(lang, q, a, _edit_provenance(draft, lang))
        # An embedding failure aborts the update, as it always has.
        vectors[lang] = await embedding_service.async_create_embeddings([q, a])
    # A single-language edit refreshes machine-made counterparts.
    translations = (
        await async_prepare_refresh(draft, next(iter(edited)))
        if len(edited) == 1
        else {}
    )

    async with async_transaction(db, "update_question"):
        # The teacher's word on difficulty beats the LLM's advisory rating.
        for field_name, value in question_data.levels().items():
            setattr(question, field_name, value)
        for lang, (q, a) in edited.items():
            question.set_text(lang, q, a, _edit_provenance(question, lang))
            await db.flush()
            await async_write_embeddings(db, question.id, lang, *vectors[lang])
        for target, translation in translations.items():
            await async_apply_translation(db, question, target, translation)
        await async_prepare_for_response(db, [question], language)

    logger.info("Question updated: id=%d", question_id)

    return question


async def reextract_concepts_for_questions(
    db: AsyncSession, question_ids: list[int]
) -> list[ConceptExtractionResult]:
    """Re-run concept extraction; each question commits independently."""
    return [await _reextract_one(db, question_id) for question_id in question_ids]


async def _reextract_one(db: AsyncSession, question_id: int) -> ConceptExtractionResult:
    """Read, extract with no connection held, then one short write ([82], [91])."""
    async with async_transaction(db, "reextract_read"):
        question = await question_repository.async_get_question(db, question_id)
    if question is None:
        return ConceptExtractionResult(question_id=question_id, success=False)

    language = question.original_language
    try:
        names = await concept_service.async_extract_concept_names(
            *question.original_text(), language=language
        )
        plans = await concept_service.async_prepare_concepts(db, names, language)
        async with async_transaction(db, "reextract_concepts"):
            await question_concept_repository.async_delete_by_question_id(
                db, question_id
            )
            concepts = await concept_service.async_apply_concepts(
                db, question_id, plans
            )
            concept_service.apply_levels_to_question(question, names)
    except Exception:
        logger.warning(
            "Concept re-extraction failed: question_id=%d", question_id, exc_info=True
        )
        return ConceptExtractionResult(question_id=question_id, success=False)

    logger.info("Concepts re-extracted: question_id=%d", question_id)
    return ConceptExtractionResult(
        question_id=question_id,
        success=True,
        concepts=[c.display_name(language) for c in concepts],
    )


async def bulk_delete_questions(
    db: AsyncSession, question_ids: list[int]
) -> tuple[int, list[int]]:
    deleted_count = 0
    not_found_ids: list[int] = []

    for question_id in question_ids:
        if await delete_question(db, question_id):
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
