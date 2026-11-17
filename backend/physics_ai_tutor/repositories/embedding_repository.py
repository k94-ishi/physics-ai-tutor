from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.models import Question, QuestionEmbedding


def _new_embedding(
    question_id: int,
    embedding: list[float],
    embedding_type: str,
    model: str,
    chunk_index: int | None,
    language: str,
) -> QuestionEmbedding:
    return QuestionEmbedding(
        question_id=question_id,
        embedding=embedding,
        type=embedding_type,
        model=model,
        chunk_index=chunk_index,
        language=language,
    )


async def create_embedding(
    db: AsyncSession,
    question_id: int,
    embedding: list[float],
    embedding_type: str,
    model: str,
    chunk_index: int | None = None,
    language: str = "ja",
) -> QuestionEmbedding:
    db_embedding = _new_embedding(
        question_id, embedding, embedding_type, model, chunk_index, language
    )

    db.add(db_embedding)
    await db.flush()

    return db_embedding


def _similar_embeddings_select(
    embedding: list[float],
    embedding_type: str = "question",
    limit: int = 10,
    exclude_question_ids: list[int] | None = None,
    exclude_statuses: list[str] | None = None,
    language: str | None = "ja",
):
    """
    SELECT question_embeddings.*, questions.*
    FROM question_embeddings
    JOIN questions
    ON question_embeddings.question_id = questions.id
    WHERE question_embeddings.type = '...'
    ORDER BY question_embeddings.embedding <=> '[...vector...]'
    LIMIT 10;

    The status filter here is what keeps unapproved rows away from
    students, so every vector search goes through this one statement.
    """
    distance = QuestionEmbedding.embedding.cosine_distance(embedding)

    query = (
        select(QuestionEmbedding, Question, distance.label("distance"))
        .join(Question, QuestionEmbedding.question_id == Question.id)
        .where(QuestionEmbedding.type == embedding_type)
    )

    if language is not None:
        query = query.where(QuestionEmbedding.language == language)

    if exclude_question_ids:
        query = query.where(Question.id.notin_(exclude_question_ids))

    if exclude_statuses:
        query = query.where(Question.status.notin_(exclude_statuses))

    return query.order_by(distance).limit(limit)


async def search_similar_embeddings(
    db: AsyncSession,
    embedding: list[float],
    embedding_type: str = "question",
    limit: int = 10,
    exclude_question_ids: list[int] | None = None,
    exclude_statuses: list[str] | None = None,
    language: str | None = "ja",
) -> list[tuple[QuestionEmbedding, Question, float]]:
    query = _similar_embeddings_select(
        embedding,
        embedding_type,
        limit,
        exclude_question_ids,
        exclude_statuses,
        language,
    )

    return [(e, question, d) for e, question, d in (await db.execute(query)).all()]


async def get_embedding(
    db: AsyncSession,
    question_id: int,
    embedding_type: str,
    language: str = "ja",
) -> list[float] | None:
    query = select(QuestionEmbedding.embedding).where(
        QuestionEmbedding.question_id == question_id,
        QuestionEmbedding.type == embedding_type,
        QuestionEmbedding.language == language,
    )

    return (await db.scalars(query)).first()


def _delete_by_question_id_statement(question_id: int, language: str | None):
    statement = sql_delete(QuestionEmbedding).where(
        QuestionEmbedding.question_id == question_id
    )

    if language is not None:
        statement = statement.where(QuestionEmbedding.language == language)

    return statement


async def delete_by_question_id(
    db: AsyncSession,
    question_id: int,
    language: str | None = None,
) -> None:
    await db.execute(_delete_by_question_id_statement(question_id, language))

    await db.flush()
