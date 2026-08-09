from sqlalchemy.orm import Session

from physics_ai_tutor.models import QuestionEmbedding


def create_embedding(
    db: Session,
    question_id: int,
    embedding: list[float],
    embedding_type: str,
    model: str,
    chunk_index: int | None = None,
) -> QuestionEmbedding:
    db_embedding = QuestionEmbedding(
        question_id=question_id,
        embedding=embedding,
        type=embedding_type,
        model=model,
        chunk_index=chunk_index,
    )
    
    db.add(db_embedding)
    db.flush()
    
    return db_embedding