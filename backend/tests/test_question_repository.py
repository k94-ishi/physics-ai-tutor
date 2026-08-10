from physics_ai_tutor.repositories import question_repository
from physics_ai_tutor.schemas.question import QuestionCreate, QuestionUpdate


def _create(db, question: str = "テスト質問", answer: str = "テスト回答"):
    return question_repository.create_question(db, question=question, answer=answer)


def test_create_question_persists(db):
    created = _create(db, "質問1", "回答1")

    assert created.id is not None
    assert created.question == "質問1"
    assert created.answer == "回答1"


def test_get_questions_returns_all(db):
    _create(db, "質問A", "回答A")
    _create(db, "質問B", "回答B")

    questions = question_repository.get_questions(db, offset=0, limit=10)

    assert len(questions) == 2
    assert {q.question for q in questions} == {"質問A", "質問B"}


def test_get_question_found(db):
    created = _create(db)

    found = question_repository.get_question(db, created.id)

    assert found is not None
    assert found.id == created.id


def test_get_question_not_found(db):
    found = question_repository.get_question(db, 99999)

    assert found is None


def test_create_questions_bulk(db):
    created = question_repository.create_questions(
        db,
        [
            QuestionCreate(question="一括質問1", answer="一括回答1"),
            QuestionCreate(question="一括質問2", answer="一括回答2"),
        ],
    )

    assert len(created) == 2
    assert all(q.id is not None for q in created)
    assert created[0].question == "一括質問1"
    assert created[1].question == "一括質問2"


def test_create_questions_bulk_empty_list(db):
    created = question_repository.create_questions(db, [])

    assert created == []


def test_delete_existing_question_returns_true(db):
    created = _create(db)

    result = question_repository.delete(db, created.id)

    assert result is True
    assert question_repository.get_question(db, created.id) is None


def test_delete_nonexistent_question_returns_false(db):
    result = question_repository.delete(db, 99999)

    assert result is False


def test_update_existing_question(db):
    created = _create(db, "更新前質問", "更新前回答")

    updated = question_repository.update(
        db,
        created.id,
        QuestionUpdate(question="更新後質問", answer="更新後回答"),
    )

    assert updated is not None
    assert updated.question == "更新後質問"
    assert updated.answer == "更新後回答"


def test_update_nonexistent_question_returns_none(db):
    updated = question_repository.update(
        db,
        99999,
        QuestionUpdate(question="更新後質問", answer="更新後回答"),
    )

    assert updated is None
