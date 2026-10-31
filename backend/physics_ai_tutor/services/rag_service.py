import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from physics_ai_tutor.core import prompts
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

    scored = [
        (result, 1 - result.distance)
        for result in results
        if 1 - result.distance > RAG_MIN_SCORE
    ]

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

    if retrieved_question_ids:
        context = load_context_by_ids(db, retrieved_question_ids, lang)
    else:
        context = retrieve_context(db, question, lang)

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
