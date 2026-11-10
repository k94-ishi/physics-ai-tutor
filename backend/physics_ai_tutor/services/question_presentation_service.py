"""Response shaping: language, concept names, references, admin extras."""

import logging

from sqlalchemy.orm import Session

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

logger = logging.getLogger(__name__)


def resolve_language(questions: list[Question], language: Language | str) -> None:
    """Populate transient `.question`, `.answer`, `.language`, `.provenance`
    with the text in `language`, falling back to the original language.
    """
    for question in questions:
        question.resolve(language)


def attach_concept_names(
    db: Session,
    questions: list[Question],
    language: Language | str = Language.JA,
    strict_language: bool = False,
) -> None:
    """Populate each question's transient `.concepts` (display names)."""
    if not questions:
        return

    concepts_by_id = question_concept_repository.get_concepts_for_questions(
        db,
        [q.id for q in questions],
        language=Language(language).value,
        strict_language=strict_language,
    )

    for question in questions:
        question.concepts = concepts_by_id.get(question.id, [])


def attach_retrieved_questions(
    db: Session,
    questions: list[Question],
    language: Language | str = Language.JA,
    strict_language: bool = False,
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
    if strict_language:
        referenced, _ = split_by_language(referenced, language)
    resolve_language(referenced, language)
    referenced_by_id = {item.id: item for item in referenced}

    for question in questions:
        question.retrieved_questions = [
            {"id": ref_id, "question": referenced_by_id[ref_id].question}
            for ref_id in question.retrieved_question_ids
            if ref_id in referenced_by_id
        ]


def prepare_for_response(
    db: Session,
    questions: list[Question],
    language: Language | str = Language.JA,
    strict_language: bool = False,
) -> None:
    """Fill the transient response fields.

    With `strict_language` (student responses) concept names and referenced
    questions that lack `language` are left out instead of falling back.
    """
    resolve_language(questions, language)
    attach_concept_names(db, questions, language, strict_language)
    attach_retrieved_questions(db, questions, language, strict_language)


def split_by_language(
    questions: list[Question], language: Language | str
) -> tuple[list[Question], list[int]]:
    """Rows that have text in `language`, and the ids of those that do not."""
    lang = Language(language)
    kept = [question for question in questions if question.has(lang)]
    missing = [question.id for question in questions if not question.has(lang)]
    return kept, missing


def attach_ai_reviews(db: Session, questions: list[Question]) -> None:
    """Expose each question's latest AI verdict; call for admins only."""
    latest = ai_review_repository.latest_for_questions(
        db, [question.id for question in questions]
    )
    for question in questions:
        row = latest.get(question.id)
        question.ai_review = (
            AiReviewSummary.model_validate(row) if row is not None else None
        )


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
