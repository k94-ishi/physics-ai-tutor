"""Review use cases: approve, edit-approve, reject, history. Async since [85].

A review reads the row, does every AI call on a detached draft with no
transaction open, then writes everything in one short transaction ([82]).
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.core.exceptions import ConceptExtractionError
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
from physics_ai_tutor.services import concept_service, embedding_service
from physics_ai_tutor.services.question_presentation_service import (
    attach_ai_reviews,
    attach_generation_meta,
    prepare_for_response,
)
from physics_ai_tutor.services.question_translation_service import (
    PreparedTranslation,
    apply_translation,
    draft_of,
    prepare_refresh,
    prepare_translation,
    write_embeddings,
)

logger = logging.getLogger(__name__)


@dataclass
class _Prepared:
    """Everything a review needs from the AI, computed before writing."""

    edit_vectors: tuple[list[float], list[float]] | None = None
    translations: dict[Language, PreparedTranslation] = field(default_factory=dict)
    concept_names: list[str] | None = None
    concept_plans: list[concept_service.PlannedSense] = field(default_factory=list)


def _provenance_for(current: Question, lang: Language) -> str:
    return (
        TextProvenance.ORIGINAL
        if lang == current.original_language
        else TextProvenance.HUMAN
    )


async def _prepare_edit(
    draft: Question, lang: Language, question: str, answer: str, prepared: _Prepared
) -> None:
    """EDIT_APPROVE: embed the teacher's text, refresh machine counterparts."""
    draft.set_text(lang, question, answer, _provenance_for(draft, lang))
    # An embedding failure aborts the review, as it did before [85].
    question_vec, answer_vec = await embedding_service.create_embeddings(
        [question, answer]
    )
    prepared.edit_vectors = (question_vec, answer_vec)
    prepared.translations.update(await prepare_refresh(draft, lang))


async def _prepare_translation(
    draft: Question,
    target: Language,
    prepared: _Prepared,
    source: Language | None = None,
) -> None:
    translation = await prepare_translation(draft, target, source)
    if translation is None:
        return
    prepared.translations[target] = translation
    # Later steps see the language as filled, as the sync code did.
    draft.set_text(
        target, translation.question, translation.answer, TextProvenance.MACHINE
    )


async def _prepare_approval(
    db: AsyncSession, draft: Question, prepared: _Prepared
) -> None:
    """Concepts from the final text, then any language still missing."""
    language = draft.original_language
    try:
        names = await concept_service.extract_concept_names(
            *draft.original_text(), language=language
        )
    except ConceptExtractionError:
        logger.warning(
            "Concept extraction failed; question saved without concepts: "
            "question_id=%d",
            draft.id,
        )
    else:
        prepared.concept_names = names
        prepared.concept_plans = await concept_service.prepare_concepts(
            db, names, language
        )
    for lang in Language:
        if not draft.has(lang):
            await _prepare_translation(draft, lang, prepared)


async def _apply(
    db: AsyncSession,
    current: Question,
    lang: Language,
    edit: tuple[str, str] | None,
    status: QuestionStatus,
    prepared: _Prepared,
) -> None:
    """Every write of one review; the caller owns the transaction."""
    if edit is not None and prepared.edit_vectors is not None:
        current.set_text(lang, *edit, _provenance_for(current, lang))
        await db.flush()
        await write_embeddings(db, current.id, lang, *prepared.edit_vectors)
    for target, translation in prepared.translations.items():
        await apply_translation(db, current, target, translation)
    await question_repository.update_status(db, current.id, status)
    if prepared.concept_names is not None:
        await concept_service.apply_concepts(db, current.id, prepared.concept_plans)
        concept_service.apply_levels_to_question(current, prepared.concept_names)


async def _present_for_admin(
    db: AsyncSession, current: Question, response_language: Language | str
) -> None:
    await prepare_for_response(db, [current], response_language)
    # Reviewing is admin-only, and the queue replaces its row with this
    # response, so it must carry the same admin fields as the list and
    # detail endpoints or the AI badge vanishes from the card.
    attach_generation_meta([current])
    await attach_ai_reviews(db, [current])


async def review_question(
    db: AsyncSession,
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
    async with transaction(db, "review_read"):
        current = await question_repository.get_question(db, question_id)
    if current is None:
        return None

    lang = Language(language) if language else Language(current.original_language)
    before = current.text(lang) or current.original_text()
    status = (
        QuestionStatus.REJECTED
        if action == QuestionReviewAction.REJECT
        else QuestionStatus.APPROVED
    )

    # The AI phase: no transaction is open here ([82]).
    draft = draft_of(current)
    prepared = _Prepared()
    edit = None
    if action == QuestionReviewAction.EDIT_APPROVE:
        assert question is not None and answer is not None
        edit = (question, answer)
        await _prepare_edit(draft, lang, question, answer, prepared)
    if status == QuestionStatus.APPROVED:
        await _prepare_approval(db, draft, prepared)

    async with transaction(db, "review_question"):
        await _apply(db, current, lang, edit, status, prepared)
        after = current.text(lang) or current.original_text()
        await question_review_repository.create(
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
        await _present_for_admin(db, current, response_language)

    logger.info(
        "Question reviewed: id=%d action=%s reviewer_id=%d language=%s",
        question_id,
        action,
        reviewer_id,
        lang,
    )
    return current


async def fetch_question_reviews(db: AsyncSession, question_id: int):
    return await question_review_repository.list_for_question(db, question_id)


async def bulk_review_questions(
    db: AsyncSession,
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
        result = await review_question(
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
