"""Read use cases: list, detail, exact match, ask cache."""

import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.database.transaction import transaction
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import (
    question_repository,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import (
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

logger = logging.getLogger(__name__)


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
    include_generation: bool = False,
    sort: str | None = None,
    ai_verdict: str | None = None,
    ids: list[int] | None = None,
    concept: str | None = None,
    concept_id: int | None = None,
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
        sort=sort,
        ai_verdict=ai_verdict,
        ids=ids,
        concept=concept,
        concept_id=concept_id,
    )

    total = question_repository.count_questions(
        db,
        keyword=keyword,
        status=status,
        exclude_statuses=exclude_statuses,
        search_question=search_question,
        search_answer=search_answer,
        language=language_filter,
        ai_verdict=ai_verdict,
        ids=ids,
        concept=concept,
        concept_id=concept_id,
    )

    prepare_for_response(db, questions, language, strict_language=only_with_language)

    # Generation metadata is admin-only; attach it while the ORM objects are
    # still in hand (the response models are built from them next).
    if include_generation:
        attach_generation_meta(questions)
        attach_ai_reviews(db, questions)

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
        with transaction(db, "lazy_translate"):
            translate_into(db, question, Language(language))

    prepare_for_response(db, [question], language, strict_language=translate_if_missing)

    return question


def fetch_question_by_exact_text(
    db: Session,
    question_text: str,
    exclude_statuses: list[str] | None = None,
    language: Language | str = Language.JA,
    strict_language: bool = False,
) -> Question | None:
    question = question_repository.get_by_exact_text(
        db, question_text, language=language, exclude_statuses=exclude_statuses
    )

    if question is not None:
        prepare_for_response(db, [question], language, strict_language)

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
