from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.openai import client
from physics_ai_tutor.models import Question, QuestionEmbedding
from physics_ai_tutor.repositories.embedding_repository import (
    search_similar_embeddings,
)


def create_embeddings(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    
    return [item.embedding for item in response.data]


def search_similar_questions(
    db: Session,
    query: str,
    limit: int = 10,
) -> list[tuple[QuestionEmbedding, Question]]:
    query_embedding = create_embeddings([query])[0]
    
    return search_similar_embeddings(
        db=db,
        embedding=query_embedding,
        embedding_type="question",
        limit=limit,
    )
    