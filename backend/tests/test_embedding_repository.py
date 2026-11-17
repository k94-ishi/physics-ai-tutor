import pytest

from physics_ai_tutor.models import QuestionEmbedding
from physics_ai_tutor.repositories import embedding_repository
from tests.conftest import create_embedding, create_question

DIM = 1536


def _vector(index: int, value: float = 1.0) -> list[float]:
    v = [0.0] * DIM
    v[index] = value
    return v


def _create_question(db, question: str = "テスト質問", answer: str = "テスト回答"):
    return create_question(db, question=question, answer=answer)


@pytest.mark.anyio
async def test_create_embedding_persists(db, async_db):
    question = _create_question(db)
    db.commit()

    created = await embedding_repository.create_embedding(
        async_db,
        question_id=question.id,
        embedding=_vector(0),
        embedding_type="question",
        model="text-embedding-3-small",
    )

    assert created.id is not None
    assert created.question_id == question.id
    assert created.type == "question"
    assert created.model == "text-embedding-3-small"


@pytest.mark.anyio
async def test_search_similar_embeddings_orders_by_distance(async_db, db):
    identical = _create_question(db, "同一質問", "同一回答")
    near = _create_question(db, "近い質問", "近い回答")
    orthogonal = _create_question(db, "遠い質問", "遠い回答")

    create_embedding(
        db,
        question_id=identical.id,
        embedding=_vector(0),
        embedding_type="question",
        model="text-embedding-3-small",
    )
    create_embedding(
        db,
        question_id=near.id,
        embedding=[0.9, 0.1] + [0.0] * (DIM - 2),
        embedding_type="question",
        model="text-embedding-3-small",
    )
    create_embedding(
        db,
        question_id=orthogonal.id,
        embedding=_vector(1),
        embedding_type="question",
        model="text-embedding-3-small",
    )

    db.commit()

    results = await embedding_repository.search_similar_embeddings(
        async_db,
        embedding=_vector(0),
        embedding_type="question",
        limit=10,
    )

    assert len(results) == 3

    ordered_question_ids = [question.id for _, question, _ in results]
    assert ordered_question_ids == [identical.id, near.id, orthogonal.id]

    distances = [distance for _, _, distance in results]
    assert distances[0] == pytest.approx(0.0, abs=1e-3)
    assert distances[1] == pytest.approx(0.0061, abs=1e-2)
    assert distances[2] == pytest.approx(1.0, abs=1e-3)
    assert distances[0] < distances[1] < distances[2]


@pytest.mark.anyio
async def test_search_similar_embeddings_filters_by_type(async_db, db):
    question = _create_question(db)

    create_embedding(
        db,
        question_id=question.id,
        embedding=_vector(1),
        embedding_type="question",
        model="text-embedding-3-small",
    )
    create_embedding(
        db,
        question_id=question.id,
        embedding=_vector(0),
        embedding_type="answer",
        model="text-embedding-3-small",
    )

    db.commit()

    results = await embedding_repository.search_similar_embeddings(
        async_db,
        embedding=_vector(0),
        embedding_type="question",
        limit=10,
    )

    assert len(results) == 1

    embedding, matched_question, distance = results[0]
    assert embedding.type == "question"
    assert matched_question.id == question.id
    assert distance == pytest.approx(1.0, abs=1e-3)


@pytest.mark.anyio
async def test_search_similar_embeddings_respects_limit(async_db, db):
    identical = _create_question(db, "同一質問", "同一回答")
    near = _create_question(db, "近い質問", "近い回答")
    orthogonal = _create_question(db, "遠い質問", "遠い回答")

    create_embedding(
        db,
        question_id=identical.id,
        embedding=_vector(0),
        embedding_type="question",
        model="text-embedding-3-small",
    )
    create_embedding(
        db,
        question_id=near.id,
        embedding=[0.9, 0.1] + [0.0] * (DIM - 2),
        embedding_type="question",
        model="text-embedding-3-small",
    )
    create_embedding(
        db,
        question_id=orthogonal.id,
        embedding=_vector(1),
        embedding_type="question",
        model="text-embedding-3-small",
    )

    db.commit()

    results = await embedding_repository.search_similar_embeddings(
        async_db,
        embedding=_vector(0),
        embedding_type="question",
        limit=2,
    )

    assert len(results) == 2

    ordered_question_ids = [question.id for _, question, _ in results]
    assert ordered_question_ids == [identical.id, near.id]


@pytest.mark.anyio
async def test_delete_by_question_id_removes_only_target_question_embeddings(
    db, async_db
):
    target = _create_question(db, "対象質問", "対象回答")
    other = _create_question(db, "他の質問", "他の回答")

    create_embedding(
        db,
        question_id=target.id,
        embedding=_vector(0),
        embedding_type="question",
        model="text-embedding-3-small",
    )
    create_embedding(
        db,
        question_id=target.id,
        embedding=_vector(0),
        embedding_type="answer",
        model="text-embedding-3-small",
    )
    create_embedding(
        db,
        question_id=other.id,
        embedding=_vector(0),
        embedding_type="question",
        model="text-embedding-3-small",
    )

    db.commit()

    await embedding_repository.delete_by_question_id(async_db, target.id)
    await async_db.commit()

    remaining = db.query(QuestionEmbedding).all()

    assert len(remaining) == 1
    assert remaining[0].question_id == other.id
