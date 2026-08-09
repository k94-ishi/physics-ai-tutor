from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.openai import client


def create_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    
    return response.data[0].embedding