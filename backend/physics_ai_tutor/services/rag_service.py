import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from physics_ai_tutor.core import prompts
from physics_ai_tutor.repositories import (
    question_concept_repository,
    question_repository,
)
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


def retrieve_context(db: Session, query: str) -> list[RetrievedQuestion]:
    """Reuse the existing similarity search + concept lookup to gather
    grounding context for a RAG answer. Only APPROVED questions are used
    as grounding, and only those above RAG_MIN_SCORE similarity.
    """
    results = embedding_service.search_similar_questions(
        db,
        query=query,
        limit=RAG_TOP_K,
        exclude_statuses=["UNREVIEWED", "REJECTED"],
    )

    scored = [
        (result, 1 - result.distance)
        for result in results
        if 1 - result.distance > RAG_MIN_SCORE
    ]

    concepts_by_id = question_concept_repository.get_concepts_for_questions(
        db, [result.id for result, _ in scored]
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


def load_context_by_ids(db: Session, ids: list[int]) -> list[RetrievedQuestion]:
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
        db, [question.id for question in ordered_questions]
    )

    return [
        RetrievedQuestion(
            id=question.id,
            question=question.question,
            answer=question.answer,
            concepts=concepts_by_id.get(question.id, []),
            score=1.0,
        )
        for question in ordered_questions
    ]


def build_context_prompt(question: str, context: list[RetrievedQuestion]) -> str:
    if not context:
        return question

    context_blocks = "\n\n".join(
        f"[参考QA{i}]\n"
        f"質問: {item.question}\n"
        f"回答: {item.answer}\n"
        f"関連概念: {', '.join(item.concepts) if item.concepts else 'なし'}"
        for i, item in enumerate(context, start=1)
    )

    return (
        f"{context_blocks}\n\n"
        "上記は参考になる可能性のある既存の質問と回答です。"
        "これらを踏まえて、以下の生徒の質問に答えてください。\n\n"
        f"質問:\n{question}"
    )


def generate_rag_answer(
    db: Session, question: str, retrieved_question_ids: list[int] | None = None
) -> tuple[str, list[int]]:
    if retrieved_question_ids:
        context = load_context_by_ids(db, retrieved_question_ids)
    else:
        context = retrieve_context(db, question)

    user_prompt = build_context_prompt(question, context)

    answer = deepseek_service.chat_completion(prompts.RAG_SYSTEM_PROMPT, user_prompt)

    logger.info(
        "RAG answer generated: question_length=%d context_count=%d",
        len(question),
        len(context),
    )

    return answer, [item.id for item in context]
