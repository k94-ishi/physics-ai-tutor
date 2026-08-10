import pytest

from physics_ai_tutor.core.exceptions import EmbeddingGenerationError
from physics_ai_tutor.schemas.question import (
    QuestionBulkCreate,
    QuestionCreate,
    QuestionUpdate,
)
from physics_ai_tutor.services import embedding_service, question_service


def _create(db, question: str = "テスト質問", answer: str = "テスト回答"):
    return question_service.create_question(
        db,
        QuestionCreate(question=question, answer=answer),
    )


def test_fetch_questions(db):
    _create(db, "質問A", "回答A")

    questions = question_service.fetch_questions(db)

    assert len(questions) == 1
    assert questions[0].question == "質問A"


def test_fetch_question_found(db):
    created = _create(db)

    found = question_service.fetch_question(db, created.id)

    assert found is not None
    assert found.id == created.id


def test_fetch_question_not_found(db):
    found = question_service.fetch_question(db, 99999)

    assert found is None


def test_create_question(db):
    created = _create(db, "質問1", "回答1")

    assert created.id is not None
    assert created.question == "質問1"
    assert created.answer == "回答1"


def test_create_questions_bulk(db):
    created = question_service.create_questions(
        db,
        QuestionBulkCreate(
            questions=[
                QuestionCreate(question="一括質問1", answer="一括回答1"),
                QuestionCreate(question="一括質問2", answer="一括回答2"),
            ]
        ),
    )

    assert len(created) == 2
    assert created[0].question == "一括質問1"


def test_create_questions_bulk_empty(db):
    created = question_service.create_questions(db, QuestionBulkCreate(questions=[]))

    assert created == []


def test_delete_question_existing_returns_true(db):
    created = _create(db)

    result = question_service.delete_question(db, created.id)

    assert result is True
    assert question_service.fetch_question(db, created.id) is None


def test_delete_question_not_found_returns_false(db):
    result = question_service.delete_question(db, 99999)

    assert result is False


def test_update_question_existing(db):
    created = _create(db, "更新前質問", "更新前回答")

    updated = question_service.update_question(
        db,
        created.id,
        QuestionUpdate(question="更新後質問", answer="更新後回答"),
    )

    assert updated is not None
    assert updated.question == "更新後質問"


def test_update_question_not_found_returns_none(db):
    updated = question_service.update_question(
        db,
        99999,
        QuestionUpdate(question="更新後質問", answer="更新後回答"),
    )

    assert updated is None


def test_create_question_rolls_back_on_embedding_failure(db, monkeypatch):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    with pytest.raises(EmbeddingGenerationError):
        _create(db)

    assert question_service.fetch_questions(db) == []
