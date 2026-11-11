from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

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


def create_embedding(
    db: Session,
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
    db.flush()

    return db_embedding


async def async_create_embedding(
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


def create_embeddings(
    db: Session,
    embeddings: list[dict],
) -> list[QuestionEmbedding]:

    db_embeddings = [QuestionEmbedding(**emb) for emb in embeddings]

    db.add_all(db_embeddings)
    db.flush()

    return db_embeddings


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

    One statement shared by the sync and async variants, so the filters -
    including the status filter that keeps unapproved rows away from
    students - cannot drift between them.
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


def search_similar_embeddings(
    db: Session,
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

    # Unpacked rather than list(...) so the declared tuple type is true.
    return [(e, question, d) for e, question, d in db.execute(query).all()]


async def async_search_similar_embeddings(
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


def get_embedding(
    db: Session,
    question_id: int,
    embedding_type: str,
    language: str = "ja",
) -> list[float] | None:
    row = (
        db.query(QuestionEmbedding.embedding)
        .filter(
            QuestionEmbedding.question_id == question_id,
            QuestionEmbedding.type == embedding_type,
            QuestionEmbedding.language == language,
        )
        .first()
    )

    return row[0] if row is not None else None


def _delete_by_question_id_statement(question_id: int, language: str | None):
    statement = sql_delete(QuestionEmbedding).where(
        QuestionEmbedding.question_id == question_id
    )

    if language is not None:
        statement = statement.where(QuestionEmbedding.language == language)

    return statement


def delete_by_question_id(
    db: Session,
    question_id: int,
    language: str | None = None,
) -> None:
    db.execute(_delete_by_question_id_statement(question_id, language))

    db.flush()


async def async_delete_by_question_id(
    db: AsyncSession,
    question_id: int,
    language: str | None = None,
) -> None:
    await db.execute(_delete_by_question_id_statement(question_id, language))

    await db.flush()
