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
    exclude_question_ids: list[int] | None = None,
    exclude_status: str | None = None,
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

    query = (
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
    )

    if exclude_question_ids:
        query = query.filter(Question.id.notin_(exclude_question_ids))

    if exclude_status is not None:
        query = query.filter(Question.status != exclude_status)

    return (
        query
        .order_by(distance)
        .limit(limit)
        .all()
    )


def get_embedding(
    db: Session,
    question_id: int,
    embedding_type: str,
) -> list[float] | None:
    row = (
        db.query(QuestionEmbedding.embedding)
        .filter(
            QuestionEmbedding.question_id == question_id,
            QuestionEmbedding.type == embedding_type,
        )
        .first()
    )

    return row[0] if row is not None else None


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
