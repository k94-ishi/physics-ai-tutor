"""Per-language text: machine translation and embeddings.

Split into a prepare phase and an apply phase ([82]): `prepare_*` talks
to DeepSeek and OpenAI and takes no session, `apply_*` writes and takes
no time. A database connection must never sit idle for the ~20 s an LLM
call takes, so the two may only meet with the connection released in
between - `translate_missing_languages` shows the pattern. The combined
`translate_into` remains for callers that already own a transaction (the
all-or-nothing import); those callers are the documented exceptions in
`test_architecture.py`.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.core import timing
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import (
    EmbeddingGenerationError,
    TranslationError,
)
from physics_ai_tutor.database.transaction import async_transaction, transaction
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import (
    embedding_repository,
    question_repository,
)
from physics_ai_tutor.schemas.language import Language, TextProvenance
from physics_ai_tutor.services import (
    embedding_service,
    translation_service,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedTranslation:
    """A finished LLM phase, waiting for a short write transaction."""

    question: str
    answer: str
    question_vector: list[float]
    answer_vector: list[float]


def _source_text(
    question: Question, source: Language | None
) -> tuple[Language, tuple[str, str]]:
    src = source or Language(question.original_language)
    text = question.text(src)
    if text is None:
        src = Language(question.original_language)
        text = question.original_text()
    return src, text


def prepare_translation(
    question: Question, target: Language, source: Language | None = None
) -> PreparedTranslation | None:
    """The LLM phase: translate and embed, no session. None on failure."""
    src, text = _source_text(question, source)

    try:
        with timing.stage("translate_qa", question_id=question.id, target=target.value):
            translated_q, translated_a = translation_service.translate_qa(
                text[0], text[1], source=src, target=target
            )
        with timing.stage(
            "embed_language", question_id=question.id, target=target.value
        ):
            question_vec, answer_vec = embedding_service.create_embeddings(
                [translated_q, translated_a]
            )
    except (TranslationError, EmbeddingGenerationError):
        logger.warning(
            "Translation skipped: question_id=%d target=%s",
            question.id,
            target,
            exc_info=True,
        )
        return None

    return PreparedTranslation(translated_q, translated_a, question_vec, answer_vec)


async def async_prepare_translation(
    question: Question, target: Language, source: Language | None = None
) -> PreparedTranslation | None:
    """As `prepare_translation`, on the event loop."""
    src, text = _source_text(question, source)

    try:
        with timing.stage("translate_qa", question_id=question.id, target=target.value):
            translated_q, translated_a = await translation_service.async_translate_qa(
                text[0], text[1], source=src, target=target
            )
        with timing.stage(
            "embed_language", question_id=question.id, target=target.value
        ):
            question_vec, answer_vec = await embedding_service.async_create_embeddings(
                [translated_q, translated_a]
            )
    except (TranslationError, EmbeddingGenerationError):
        logger.warning(
            "Translation skipped: question_id=%d target=%s",
            question.id,
            target,
            exc_info=True,
        )
        return None

    return PreparedTranslation(translated_q, translated_a, question_vec, answer_vec)


def write_embeddings(
    db: Session,
    question_id: int,
    language: Language,
    question_vector: list[float],
    answer_vector: list[float],
) -> None:
    """Replace one language's embedding rows; the caller commits."""
    embedding_repository.delete_by_question_id(db, question_id, language=language)

    for embedding_type, vector in (
        ("question", question_vector),
        ("answer", answer_vector),
    ):
        embedding_repository.create_embedding(
            db,
            question_id=question_id,
            embedding=vector,
            embedding_type=embedding_type,
            model=settings.embedding_model,
            language=language.value,
        )


async def async_write_embeddings(
    db: AsyncSession,
    question_id: int,
    language: Language,
    question_vector: list[float],
    answer_vector: list[float],
) -> None:
    """Replace one language's embedding rows; the caller commits."""
    await embedding_repository.async_delete_by_question_id(
        db, question_id, language=language
    )

    for embedding_type, vector in (
        ("question", question_vector),
        ("answer", answer_vector),
    ):
        await embedding_repository.async_create_embedding(
            db,
            question_id=question_id,
            embedding=vector,
            embedding_type=embedding_type,
            model=settings.embedding_model,
            language=language.value,
        )


def apply_translation(
    db: Session, question: Question, target: Language, prepared: PreparedTranslation
) -> None:
    """The write phase: text and its embeddings together, never apart."""
    question.set_text(
        target, prepared.question, prepared.answer, TextProvenance.MACHINE
    )
    db.flush()
    write_embeddings(
        db, question.id, target, prepared.question_vector, prepared.answer_vector
    )

    logger.info("Question translated: question_id=%d target=%s", question.id, target)


async def async_apply_translation(
    db: AsyncSession,
    question: Question,
    target: Language,
    prepared: PreparedTranslation,
) -> None:
    """The write phase: text and its embeddings together, never apart."""
    question.set_text(
        target, prepared.question, prepared.answer, TextProvenance.MACHINE
    )
    await db.flush()
    await async_write_embeddings(
        db, question.id, target, prepared.question_vector, prepared.answer_vector
    )

    logger.info("Question translated: question_id=%d target=%s", question.id, target)


def embed_language(db: Session, question: Question, language: Language) -> None:
    """Embed one language's existing text; the caller owns the transaction.

    Still used by the admin write paths, which hold their transaction
    across this OpenAI call - the documented exceptions of [82], reworked
    with [73]/[76].
    """
    text = question.text(language)
    if text is None:
        return

    question_vec, answer_vec = embedding_service.create_embeddings(list(text))
    write_embeddings(db, question.id, language, question_vec, answer_vec)


def translate_into(
    db: Session, question: Question, target: Language, source: Language | None = None
) -> bool:
    """Prepare and apply in one call, for a caller that owns a transaction.

    Best effort; returns success. Inside the caller's transaction the
    connection stays held across the LLM phase, which is why the
    transaction-owning paths below use prepare/apply instead.
    """
    prepared = prepare_translation(question, target, source)
    if prepared is None:
        return False

    apply_translation(db, question, target, prepared)
    return True


def translate_missing(db: Session, question: Question) -> list[Language]:
    """Fill every missing language; the caller owns the transaction."""
    filled = [
        lang
        for lang in Language
        if not question.has(lang) and translate_into(db, question, lang)
    ]
    return filled


def refresh_machine_translations(
    db: Session, question: Question, edited: Language
) -> None:
    """After a human edit in `edited`, regenerate machine-made counterparts."""
    for lang in Language:
        if lang == edited:
            continue
        if question.provenance_of(lang) == TextProvenance.MACHINE or not question.has(
            lang
        ):
            translate_into(db, question, lang, source=edited)


def translate_missing_languages(db: Session, question_id: int) -> list[Language]:
    """Fill every missing language of one question; commits on its own.

    Used by the admin endpoint, the backfill CLI and the background
    list-translation task. The connection is released before each LLM
    phase and taken again only for the short write ([82]); each language
    commits on its own, which [53] allows - its guarantee is that a
    translated row never re-enters the queue, not that both languages
    appear atomically.
    """
    with transaction(db, "translate_missing_read"):
        question = question_repository.get_question(db, question_id)

    if question is None:
        return []

    filled = []
    for lang in Language:
        if question.has(lang):
            continue
        prepared = prepare_translation(question, lang)
        if prepared is None:
            continue
        with transaction(db, "translate_missing_write"):
            apply_translation(db, question, lang, prepared)
        filled.append(lang)
    return filled


async def async_translate_missing_languages(
    db: AsyncSession, question_id: int
) -> list[Language]:
    """As `translate_missing_languages`; the post-ask background task."""
    async with async_transaction(db, "translate_missing_read"):
        question = await db.get(Question, question_id)

    if question is None:
        return []

    filled = []
    for lang in Language:
        if question.has(lang):
            continue
        prepared = await async_prepare_translation(question, lang)
        if prepared is None:
            continue
        async with async_transaction(db, "translate_missing_write"):
            await async_apply_translation(db, question, lang, prepared)
        filled.append(lang)
    return filled
