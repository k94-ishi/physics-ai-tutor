"""Response shaping: language, concept names, references, admin extras.

Async only since [94]; the shaping rules live in the pure `_set_*`
helpers ([83]).
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.models.ai_review import AiReview
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import (
    ai_review_repository,
    question_concept_repository,
    question_repository,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import (
    AiReviewSummary,
    GenerationMeta,
)
from physics_ai_tutor.services.response_language import (
    ResponseLanguage,
    TranslationNeeds,
)

logger = logging.getLogger(__name__)


def resolve_language(questions: list[Question], language: Language | str) -> None:
    """Populate transient `.question`, `.answer`, `.language`, `.provenance`
    with the text in `language`, falling back to the original language.
    """
    for question in questions:
        question.resolve(language)


def _set_concept_names(
    questions: list[Question], concepts_by_id: dict[int, list[str]]
) -> None:
    for question in questions:
        question.concepts = concepts_by_id.get(question.id, [])


async def async_attach_concept_names(
    db: AsyncSession,
    questions: list[Question],
    language: Language | str = Language.JA,
    strict: bool = False,
) -> None:
    """As `attach_concept_names` ([83])."""
    if not questions:
        return

    concepts_by_id = await question_concept_repository.async_get_concepts_for_questions(
        db,
        [q.id for q in questions],
        language=Language(language).value,
        strict=strict,
    )
    _set_concept_names(questions, concepts_by_id)


def _referenced_ids(questions: list[Question]) -> set[int]:
    return {
        question_id
        for question in questions
        for question_id in question.retrieved_question_ids
    }


def _set_retrieved_questions(
    questions: list[Question],
    referenced: list[Question],
    language: Language | str,
    strict: bool,
) -> None:
    """Map `retrieved_question_ids` to {id, question} summaries in `language`."""
    if strict:
        referenced, _ = ResponseLanguage(Language(language), strict=True).readable(
            referenced
        )
    resolve_language(referenced, language)
    referenced_by_id = {item.id: item for item in referenced}

    for question in questions:
        question.retrieved_questions = [
            {"id": ref_id, "question": referenced_by_id[ref_id].question}
            for ref_id in question.retrieved_question_ids
            if ref_id in referenced_by_id
        ]


async def async_attach_retrieved_questions(
    db: AsyncSession,
    questions: list[Question],
    language: Language | str = Language.JA,
    strict: bool = False,
) -> None:
    """As `attach_retrieved_questions` ([83])."""
    if not questions:
        return

    all_ids = _referenced_ids(questions)
    referenced = (
        await question_repository.async_get_questions_by_ids(db, list(all_ids))
        if all_ids
        else []
    )
    _set_retrieved_questions(questions, referenced, language, strict)


def _needs_for(
    questions: list[Question], response: ResponseLanguage
) -> TranslationNeeds:
    if not response.strict:
        return TranslationNeeds()
    return TranslationNeeds(concept_question_ids=[q.id for q in questions])


async def async_prepare_for_response(
    db: AsyncSession,
    questions: list[Question],
    language: Language | str | ResponseLanguage = Language.JA,
) -> TranslationNeeds:
    """As `prepare_for_response` ([83]); the sync one serves the admin writers."""
    response = ResponseLanguage.of(language)
    resolve_language(questions, response.language)
    await async_attach_concept_names(db, questions, response.language, response.strict)
    await async_attach_retrieved_questions(
        db, questions, response.language, response.strict
    )
    return _needs_for(questions, response)


def _set_ai_reviews(questions: list[Question], latest: dict[int, AiReview]) -> None:
    for question in questions:
        row = latest.get(question.id)
        question.ai_review = (
            AiReviewSummary.model_validate(row) if row is not None else None
        )


async def async_attach_ai_reviews(db: AsyncSession, questions: list[Question]) -> None:
    """As `attach_ai_reviews` ([83])."""
    latest = await ai_review_repository.async_latest_for_questions(
        db, [question.id for question in questions]
    )
    _set_ai_reviews(questions, latest)


def attach_generation_meta(questions: list[Question]) -> None:
    """Expose generation metadata to the response; call for admins only."""
    for question in questions:
        question.generation = GenerationMeta(
            model=question.generation_model,
            prompt_version=question.prompt_version,
            mode=question.generation_mode,
            prompt_tokens=question.prompt_tokens,
            completion_tokens=question.completion_tokens,
        )
