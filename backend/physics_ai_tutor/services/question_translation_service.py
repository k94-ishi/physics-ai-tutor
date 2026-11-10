"""Per-language text: machine translation and embeddings."""

import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import (
    EmbeddingGenerationError,
    TranslationError,
)
from physics_ai_tutor.database.transaction import transaction
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


def embed_language(db: Session, question: Question, language: Language) -> None:
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


def translate_into(
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
        embed_language(db, question, target)
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


def translate_missing(db: Session, question: Question) -> list[Language]:
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

    Used by the background task after an AI answer, the admin endpoint, and
    the backfill CLI.
    """
    question = question_repository.get_question(db, question_id)

    if question is None:
        return []

    with transaction(db, "translate_missing"):
        filled = translate_missing(db, question)
    return filled
