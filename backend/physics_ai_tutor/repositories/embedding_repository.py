from sqlalchemy.orm import Session

from physics_ai_tutor.models import Question, QuestionEmbedding


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


def create_embeddings(
    db: Session,
    embeddings: list[dict],
) -> list[QuestionEmbedding]:
    
    db_embeddings = [QuestionEmbedding(**emb) for emb in embeddings]
    
    db.add_all(db_embeddings)
    db.flush()
    
    return db_embeddings


def search_similar_embeddings(
    db: Session,
    embedding: list[float],
    embedding_type: str = "question",
    limit: int = 10,
) -> list[tuple[QuestionEmbedding, Question, float]]:
    """
    SELECT question_embeddings.*, questions.*
    FROM question_embeddings
    JOIN questions
    ON question_embeddings.question_id = questions.id
    WHERE question_embeddings.type = '...'
    ORDER BY question_embeddings.embedding <=> '[...vector...]'
    LIMIT 10;
    """
    distance = QuestionEmbedding.embedding.cosine_distance(embedding)
    
    return (
        db.query(
            QuestionEmbedding,
            Question,
            distance.label("distance")
        )
        .join(
            Question,
            QuestionEmbedding.question_id == Question.id,
        )
        .filter(QuestionEmbedding.type == embedding_type)
        .order_by(distance)
        .limit(limit)
        .all()
    )


def delete_by_question_id(
    db: Session,
    question_id: int,
) -> None:
    
    (
        db.query(QuestionEmbedding)
        .filter(QuestionEmbedding.question_id == question_id)
        .delete()
    )
    
    db.flush()
