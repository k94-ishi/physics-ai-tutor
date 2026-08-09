from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.openai import client


def create_embeddings(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    
    return [item.embedding for item in response.data]