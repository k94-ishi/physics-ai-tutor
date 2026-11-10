"""Review use cases: approve, edit-approve, reject, history."""

import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.database.transaction import transaction
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import (
    question_repository,
    question_review_repository,
)
from physics_ai_tutor.schemas.language import Language, TextProvenance
from physics_ai_tutor.schemas.question import (
    QuestionStatus,
)
from physics_ai_tutor.schemas.question_review import QuestionReviewAction
from physics_ai_tutor.services.question_presentation_service import (
    attach_ai_reviews,
    attach_generation_meta,
    prepare_for_response,
)
from physics_ai_tutor.services.question_translation_service import (
    embed_language,
    refresh_machine_translations,
    translate_missing,
)
from physics_ai_tutor.services.question_write_service import (
    attach_concepts_best_effort,
)

logger = logging.getLogger(__name__)


def _apply_edit(
    db: Session, current: Question, lang: Language, question: str, answer: str
) -> None:
    """EDIT_APPROVE: store the teacher's text, re-embed, refresh translations."""
    provenance = (
        TextProvenance.ORIGINAL
        if lang == current.original_language
        else TextProvenance.HUMAN
    )
    current.set_text(lang, question, answer, provenance)
    db.flush()
    embed_language(db, current, lang)
    refresh_machine_translations(db, current, lang)


def _set_status(db: Session, current: Question, status: QuestionStatus) -> None:
    question_repository.update_status(db, current.id, status)
    # Concept extraction is triggered by the status becoming APPROVED.
    if status == QuestionStatus.APPROVED:
        attach_concepts_best_effort(db, current)
        translate_missing(db, current)


def _present_for_admin(
    db: Session, current: Question, response_language: Language | str
) -> None:
    prepare_for_response(db, [current], response_language)
    # Reviewing is admin-only, and the queue replaces its row with this
    # response, so it must carry the same admin fields as the list and
    # detail endpoints or the AI badge vanishes from the card.
    attach_generation_meta([current])
    attach_ai_reviews(db, [current])


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
    """Approve, edit-approve or reject; the review row keeps before/after."""
    with transaction(db, "review_question"):
        current = question_repository.get_question(db, question_id)
        if current is None:
            return None

        lang = Language(language) if language else Language(current.original_language)
        before = current.text(lang) or current.original_text()

        if action == QuestionReviewAction.EDIT_APPROVE:
            assert question is not None and answer is not None
            _apply_edit(db, current, lang, question, answer)
        _set_status(
            db,
            current,
            QuestionStatus.REJECTED
            if action == QuestionReviewAction.REJECT
            else QuestionStatus.APPROVED,
        )

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
        _present_for_admin(db, current, response_language)

    logger.info(
        "Question reviewed: id=%d action=%s reviewer_id=%d language=%s",
        question_id,
        action,
        reviewer_id,
        lang,
    )
    return current


def fetch_question_reviews(db: Session, question_id: int):
    return question_review_repository.list_for_question(db, question_id)


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
