import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from physics_ai_tutor.core import prompts, timing
from physics_ai_tutor.repositories import (
    question_concept_repository,
    question_repository,
)
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.schemas.question import QuestionStatus
from physics_ai_tutor.services import deepseek_service, embedding_service

logger = logging.getLogger(__name__)

RAG_TOP_K = 5
RAG_MIN_SCORE = 0.5


@dataclass
class RetrievedQuestion:
    id: int
    question: str
    answer: str
    concepts: list[str]
    score: float


def retrieve_context(
    db: Session, query: str, language: Language = Language.JA
) -> list[RetrievedQuestion]:
    """Reuse the existing similarity search + concept lookup to gather
    grounding context for a RAG answer. Only APPROVED questions are used
    as grounding, and only those above RAG_MIN_SCORE similarity.
    """
    results = embedding_service.search_similar_questions(
        db,
        query=query,
        limit=RAG_TOP_K,
        exclude_statuses=["UNREVIEWED", "REJECTED"],
        language=language,
    )

    scored = _scored(results)

    concepts_by_id = question_concept_repository.get_concepts_for_questions(
        db, [result.id for result, _ in scored], language=language.value
    )

    return [
        RetrievedQuestion(
            id=result.id,
            question=result.question,
            answer=result.answer,
            concepts=concepts_by_id.get(result.id, []),
            score=score,
        )
        for result, score in scored
    ]


def load_context_by_ids(
    db: Session, ids: list[int], language: Language = Language.JA
) -> list[RetrievedQuestion]:
    """Build grounding context from client-selected question IDs (e.g. the
    results the user already saw from a prior similarity search), skipping
    a fresh embedding search. IDs are capped to RAG_TOP_K and filtered down
    to APPROVED questions only - the IDs come from the client, so this
    re-checks status server-side rather than trusting them as-is.
    """
    capped_ids = ids[:RAG_TOP_K]
    questions_by_id = {
        question.id: question
        for question in question_repository.get_questions_by_ids(db, capped_ids)
        if question.status == QuestionStatus.APPROVED
    }
    ordered_questions = [
        questions_by_id[question_id]
        for question_id in capped_ids
        if question_id in questions_by_id
    ]

    concepts_by_id = question_concept_repository.get_concepts_for_questions(
        db, [question.id for question in ordered_questions], language=language.value
    )

    context = []
    for question in ordered_questions:
        # Prefer the student's language; the LLM copes with mixed context.
        text = question.text(language) or question.original_text()
        context.append(
            RetrievedQuestion(
                id=question.id,
                question=text[0],
                answer=text[1],
                concepts=concepts_by_id.get(question.id, []),
                score=1.0,
            )
        )

    return context


def build_context_prompt(
    question: str, context: list[RetrievedQuestion], language: Language = Language.JA
) -> str:
    if not context:
        return question

    labels = prompts.RAG_CONTEXT_LABELS[language]
    context_blocks = "\n\n".join(
        f"[{labels['block'].format(index=i)}]\n"
        f"{labels['question']}: {item.question}\n"
        f"{labels['answer']}: {item.answer}\n"
        f"{labels['concepts']}: "
        f"{', '.join(item.concepts) if item.concepts else labels['none']}"
        for i, item in enumerate(context, start=1)
    )

    return (
        f"{context_blocks}\n\n"
        f"{labels['instruction']}\n\n"
        f"{labels['question']}:\n{question}"
    )


def generate_rag_answer(
    db: Session,
    question: str,
    retrieved_question_ids: list[int] | None = None,
    language: Language | str = Language.JA,
) -> tuple[deepseek_service.GenerationResult, list[int]]:
    lang = Language(language)

    with timing.stage("rag_context") as stage:
        if retrieved_question_ids:
            stage.note(source="client_ids")
            context = load_context_by_ids(db, retrieved_question_ids, lang)
        else:
            stage.note(source="search")
            context = retrieve_context(db, question, lang)
        stage.note(count=len(context))

    user_prompt = build_context_prompt(question, context, lang)

    result = deepseek_service.generate_answer(
        prompts.RAG_SYSTEM_PROMPTS[lang], user_prompt
    )

    logger.info(
        "RAG answer generated: question_length=%d context_count=%d",
        len(question),
        len(context),
    )

    return result, [item.id for item in context]


def _scored(results) -> list[tuple]:
    """Keep only results above the grounding threshold, with their score."""
    return [
        (result, 1 - result.distance)
        for result in results
        if 1 - result.distance > RAG_MIN_SCORE
    ]


async def async_retrieve_context(
    db: AsyncSession, query: str, language: Language = Language.JA
) -> list[RetrievedQuestion]:
    """As `retrieve_context`, on the event loop ([70])."""
    results = await embedding_service.async_search_similar_questions(
        db,
        query=query,
        limit=RAG_TOP_K,
        exclude_statuses=["UNREVIEWED", "REJECTED"],
        language=language,
    )

    scored = _scored(results)

    concepts_by_id = await question_concept_repository.async_get_concepts_for_questions(
        db, [result.id for result, _ in scored], language=language.value
    )

    return [
        RetrievedQuestion(
            id=result.id,
            question=result.question,
            answer=result.answer,
            concepts=concepts_by_id.get(result.id, []),
            score=score,
        )
        for result, score in scored
    ]


async def async_load_context_by_ids(
    db: AsyncSession, ids: list[int], language: Language = Language.JA
) -> list[RetrievedQuestion]:
    """As `load_context_by_ids`; still re-checks status server-side ([70])."""
    capped_ids = ids[:RAG_TOP_K]
    questions_by_id = {
        question.id: question
        for question in await question_repository.async_get_questions_by_ids(
            db, capped_ids
        )
        if question.status == QuestionStatus.APPROVED
    }
    ordered_questions = [
        questions_by_id[question_id]
        for question_id in capped_ids
        if question_id in questions_by_id
    ]

    concepts_by_id = await question_concept_repository.async_get_concepts_for_questions(
        db, [question.id for question in ordered_questions], language=language.value
    )

    context = []
    for question in ordered_questions:
        # Prefer the student's language; the LLM copes with mixed context.
        text = question.text(language) or question.original_text()
        context.append(
            RetrievedQuestion(
                id=question.id,
                question=text[0],
                answer=text[1],
                concepts=concepts_by_id.get(question.id, []),
                score=1.0,
            )
        )

    return context


async def async_generate_rag_answer(
    db: AsyncSession,
    question: str,
    retrieved_question_ids: list[int] | None = None,
    language: Language | str = Language.JA,
) -> tuple[deepseek_service.GenerationResult, list[int]]:
    """As `generate_rag_answer`, on the event loop ([70])."""
    lang = Language(language)

    with timing.stage("rag_context") as stage:
        if retrieved_question_ids:
            stage.note(source="client_ids")
            context = await async_load_context_by_ids(db, retrieved_question_ids, lang)
        else:
            stage.note(source="search")
            context = await async_retrieve_context(db, question, lang)
        stage.note(count=len(context))

    user_prompt = build_context_prompt(question, context, lang)

    result = await deepseek_service.async_generate_answer(
        prompts.RAG_SYSTEM_PROMPTS[lang], user_prompt
    )

    logger.info(
        "RAG answer generated: question_length=%d context_count=%d",
        len(question),
        len(context),
    )

    return result, [item.id for item in context]
