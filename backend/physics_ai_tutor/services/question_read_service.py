"""Read use cases: list, detail, exact match, ask cache."""

import logging
from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.database.transaction import transaction
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import (
    question_repository,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import (
    QuestionFilters,
    QuestionListResponse,
    QuestionStatus,
)
from physics_ai_tutor.services.question_presentation_service import (
    attach_ai_reviews,
    attach_generation_meta,
    prepare_for_response,
)
from physics_ai_tutor.services.question_translation_service import (
    translate_into,
)
from physics_ai_tutor.services.response_language import (
    ResponseLanguage,
    TranslationNeeds,
)

logger = logging.getLogger(__name__)


def fetch_questions(
    db: Session,
    page: int,
    size: int,
    filters: QuestionFilters | None = None,
    language: Language | str | ResponseLanguage = Language.JA,
    sort: str | None = None,
    include_admin_fields: bool = False,
) -> QuestionListResponse:
    """One page of questions; strict readers only get rows in their language."""
    response = ResponseLanguage.of(language)
    filters = filters or QuestionFilters()
    if response.strict:
        filters = replace(filters, language=response.language)

    questions = question_repository.get_questions(
        db, offset=(page - 1) * size, limit=size, filters=filters, sort=sort
    )
    total = question_repository.count_questions(db, filters)
    prepare_for_response(db, questions, response)

    # Admin-only fields; attach them while the ORM objects are still in hand.
    if include_admin_fields:
        attach_generation_meta(questions)
        attach_ai_reviews(db, questions)

    logger.info(
        "Questions fetched: page=%d size=%d keyword_present=%s results=%d total=%d",
        page,
        size,
        filters.keyword is not None,
        len(questions),
        total,
    )
    return QuestionListResponse(items=questions, total=total, page=page, size=size)


def fetch_question(
    db: Session,
    question_id: int,
    exclude_statuses: list[str] | None = None,
    language: Language | str | ResponseLanguage = Language.JA,
) -> tuple[Question | None, TranslationNeeds]:
    """One question; a strict reader gets a missing language translated now."""
    response = ResponseLanguage.of(language)
    question = question_repository.get_question(
        db, question_id, exclude_statuses=exclude_statuses
    )
    if question is None:
        return None, TranslationNeeds()

    # Lazy fill for rows approved before translation existed.
    if response.strict and not question.has(response.language):
        with transaction(db, "lazy_translate"):
            translate_into(db, question, response.language)

    return question, prepare_for_response(db, [question], response)


def fetch_question_by_exact_text(
    db: Session,
    question_text: str,
    exclude_statuses: list[str] | None = None,
    language: Language | str | ResponseLanguage = Language.JA,
) -> Question | None:
    response = ResponseLanguage.of(language)
    question = question_repository.get_by_exact_text(
        db,
        question_text,
        language=response.language,
        exclude_statuses=exclude_statuses,
    )
    if question is not None:
        prepare_for_response(db, [question], response)
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


async def async_find_cached_answer(
    db: AsyncSession, question_text: str, language: Language | str
) -> Question | None:
    """As `find_cached_answer`, on the event loop ([70])."""
    return await question_repository.async_get_by_exact_text(
        db,
        question_text,
        language=language,
        exclude_statuses=[QuestionStatus.REJECTED],
    )
