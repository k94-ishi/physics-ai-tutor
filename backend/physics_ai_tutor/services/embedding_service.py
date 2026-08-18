import logging

from openai import OpenAIError
from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import EmbeddingGenerationError
from physics_ai_tutor.core.openai import client
from physics_ai_tutor.repositories.embedding_repository import (
    search_similar_embeddings,
)
from physics_ai_tutor.schemas.embedding import SimilarQuestionResponse

logger = logging.getLogger(__name__)


def create_embeddings(texts: list[str]) -> list[list[float]]:
    logger.debug("Generating embeddings: count=%d", len(texts))

    try:
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
    except OpenAIError as exc:
        logger.warning("OpenAI embedding generation failed: %s", type(exc).__name__)
        raise EmbeddingGenerationError(
            "Failed to generate embeddings via OpenAI API."
        ) from exc

    logger.info(
        "Generated embeddings: count=%d model=%s", len(texts), settings.embedding_model
    )

    return [item.embedding for item in response.data]


def search_similar_questions(
    db: Session,
    query: str,
    limit: int = 10,
    exclude_statuses: list[str] | None = None,
) -> list[SimilarQuestionResponse]:
    query_embedding = create_embeddings([query])[0]

    results = search_similar_embeddings(
        db=db,
        embedding=query_embedding,
        embedding_type="question",
        limit=limit,
        exclude_statuses=exclude_statuses,
    )

    logger.info(
        "Similar question search completed: query_length=%d limit=%d results=%d",
        len(query),
        limit,
        len(results),
    )

    return [
        SimilarQuestionResponse(
            id=question.id,
            question=question.question,
            answer=question.answer,
            distance=distance,
        )
        for _, question, distance in results
    ]
