import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from physics_ai_tutor.core import prompts
from physics_ai_tutor.repositories import question_concept_repository
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


def generate_rag_answer(db: Session, question: str) -> tuple[str, list[int]]:
    context = retrieve_context(db, question)
    user_prompt = build_context_prompt(question, context)

    answer = deepseek_service.chat_completion(prompts.RAG_SYSTEM_PROMPT, user_prompt)

    logger.info(
        "RAG answer generated: question_length=%d context_count=%d",
        len(question),
        len(context),
    )

    return answer, [item.id for item in context]
