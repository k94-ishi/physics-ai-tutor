from openai import OpenAIError
from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import EmbeddingGenerationError
from physics_ai_tutor.core.openai import client
from physics_ai_tutor.repositories.embedding_repository import (
    search_similar_embeddings,
)
from physics_ai_tutor.schemas.embedding import SimilarQuestionResponse


def create_embeddings(texts: list[str]) -> list[list[float]]:
    try:
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
    except OpenAIError as exc:
        raise EmbeddingGenerationError(
            "Failed to generate embeddings via OpenAI API."
        ) from exc

    return [item.embedding for item in response.data]


def search_similar_questions(
    db: Session,
    query: str,
    limit: int = 10,
) -> list[SimilarQuestionResponse]:
    query_embedding = create_embeddings([query])[0]
    
    results = search_similar_embeddings(
        db=db,
        embedding=query_embedding,
        embedding_type="question",
        limit=limit,
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
    