import pytest

from physics_ai_tutor.repositories import question_repository
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionFilters,
    QuestionUpdate,
)


def _create(db, question: str = "テスト質問", answer: str = "テスト回答", **extra):
    # Committed so the async readers under test can see the row ([83]).
    created = question_repository.create_question(
        db, question=question, answer=answer, **extra
    )
    db.commit()
    return created


def test_create_question_persists(db):
    created = _create(db, "質問1", "回答1")

    assert created.id is not None
    assert created.question == "質問1"
    assert created.answer == "回答1"


@pytest.mark.anyio
async def test_get_questions_returns_all(db, async_db):
    _create(db, "質問A", "回答A")
    _create(db, "質問B", "回答B")

    questions = await question_repository.get_questions(async_db, offset=0, limit=10)

    assert len(questions) == 2
    assert {q.question for q in questions} == {"質問A", "質問B"}


@pytest.mark.anyio
async def test_get_questions_respects_offset_and_limit(db, async_db):
    _create(db, "質問A", "回答A")
    _create(db, "質問B", "回答B")
    _create(db, "質問C", "回答C")

    questions = await question_repository.get_questions(async_db, offset=1, limit=1)

    assert len(questions) == 1


@pytest.mark.anyio
async def test_count_questions_returns_total(db, async_db):
    _create(db, "質問A", "回答A")
    _create(db, "質問B", "回答B")

    assert await question_repository.count_questions(async_db) == 2


@pytest.mark.anyio
async def test_get_questions_filters_by_keyword_in_question(db, async_db):
    matching = _create(db, "運動量保存則とは何ですか", "運動量は保存されます")
    _create(db, "エネルギー保存則とは何ですか", "エネルギーは保存されます")

    questions = await question_repository.get_questions(
        async_db, offset=0, limit=10, filters=QuestionFilters(keyword="運動量")
    )

    assert [q.id for q in questions] == [matching.id]


@pytest.mark.anyio
async def test_get_questions_filters_by_keyword_in_answer(db, async_db):
    matching = _create(db, "第一法則とは", "運動量は保存されます")
    _create(db, "第二法則とは", "力は質量と加速度の積です")

    questions = await question_repository.get_questions(
        async_db, offset=0, limit=10, filters=QuestionFilters(keyword="運動量")
    )

    assert [q.id for q in questions] == [matching.id]


@pytest.mark.anyio
async def test_count_questions_filters_by_keyword(db, async_db):
    _create(db, "運動量保存則とは何ですか", "運動量は保存されます")
    _create(db, "エネルギー保存則とは何ですか", "エネルギーは保存されます")

    assert await question_repository.count_questions(
        async_db, filters=QuestionFilters(keyword="運動量")
    )


@pytest.mark.anyio
async def test_get_questions_keyword_no_match_returns_empty(db, async_db):
    _create(db, "運動量保存則とは何ですか", "運動量は保存されます")

    questions = await question_repository.get_questions(
        async_db,
        offset=0,
        limit=10,
        filters=QuestionFilters(keyword="存在しないキーワード"),
    )

    assert questions == []


@pytest.mark.anyio
async def test_get_questions_keyword_and_across_terms(db, async_db):
    matching = _create(
        db, "運動量保存則とは何ですか", "衝突の前後で運動量は保存されます"
    )
    _create(db, "運動量保存則とは何ですか", "エネルギーは保存されます")
    _create(db, "衝突とは何ですか", "衝突の説明です")

    questions = await question_repository.get_questions(
        async_db, offset=0, limit=10, filters=QuestionFilters(keyword="運動量 衝突")
    )

    assert [q.id for q in questions] == [matching.id]


@pytest.mark.anyio
async def test_get_questions_keyword_search_question_only(db, async_db):
    matching = _create(db, "運動量保存則とは何ですか", "回答")
    _create(db, "第一法則とは", "運動量は保存されます")

    questions = await question_repository.get_questions(
        async_db,
        offset=0,
        limit=10,
        filters=QuestionFilters(
            keyword="運動量", search_question=True, search_answer=False
        ),
    )

    assert [q.id for q in questions] == [matching.id]


@pytest.mark.anyio
async def test_get_questions_keyword_search_answer_only(db, async_db):
    _create(db, "運動量保存則とは何ですか", "回答")
    matching = _create(db, "第一法則とは", "運動量は保存されます")

    questions = await question_repository.get_questions(
        async_db,
        offset=0,
        limit=10,
        filters=QuestionFilters(
            keyword="運動量", search_question=False, search_answer=True
        ),
    )

    assert [q.id for q in questions] == [matching.id]


def test_get_question_found(db):
    created = _create(db)

    found = question_repository.get_question(db, created.id)

    assert found is not None
    assert found.id == created.id


def test_get_question_not_found(db):
    found = question_repository.get_question(db, 99999)

    assert found is None


@pytest.mark.anyio
async def test_async_get_question_applies_exclude_statuses(db, async_db):
    created = _create(db, "却下済み", "回答", status="REJECTED")

    found = await question_repository.async_get_question(async_db, created.id)
    hidden = await question_repository.async_get_question(
        async_db, created.id, exclude_statuses=["REJECTED"]
    )

    assert found is not None and found.id == created.id
    assert hidden is None


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


@pytest.mark.anyio
async def test_delete_existing_question_returns_true(db, async_db):
    created = _create(db)

    # Read before the delete: the row is gone afterwards.
    created_id = created.id
    result = await question_repository.delete(async_db, created_id)
    await async_db.commit()
    db.expire_all()

    assert result is True
    assert question_repository.get_question(db, created_id) is None


@pytest.mark.anyio
async def test_delete_nonexistent_question_returns_false(db, async_db):
    result = await question_repository.delete(async_db, 99999)

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


def test_get_by_exact_text_found(db):
    created = _create(db, "完全一致質問", "回答")

    found = question_repository.get_by_exact_text(db, "完全一致質問")

    assert found is not None
    assert found.id == created.id


def test_get_by_exact_text_not_found(db):
    found = question_repository.get_by_exact_text(db, "存在しない質問")

    assert found is None


def test_get_by_exact_text_excludes_status(db):
    question_repository.create_question(
        db, question="却下済み質問", answer="回答", status="REJECTED"
    )

    found = question_repository.get_by_exact_text(
        db, "却下済み質問", exclude_statuses=["REJECTED"]
    )

    assert found is None


def test_get_by_exact_text_includes_unreviewed_by_default(db):
    created = question_repository.create_question(
        db, question="未レビュー質問", answer="回答", status="UNREVIEWED"
    )

    found = question_repository.get_by_exact_text(
        db, "未レビュー質問", exclude_statuses=["REJECTED"]
    )

    assert found is not None
    assert found.id == created.id


def test_create_question_with_status_and_source(db):
    created = question_repository.create_question(
        db,
        question="質問",
        answer="回答",
        status="UNREVIEWED",
        source="AI_GENERATED",
    )

    assert created.status == "UNREVIEWED"
    assert created.source == "AI_GENERATED"


@pytest.mark.anyio
async def test_get_questions_excludes_status(db, async_db):
    _create(db, "質問A", "回答A")
    rejected = _create(db, "質問B", "回答B", status="REJECTED")

    questions = await question_repository.get_questions(
        async_db,
        offset=0,
        limit=10,
        filters=QuestionFilters(exclude_statuses=["REJECTED"]),
    )

    assert rejected.id not in [q.id for q in questions]


@pytest.mark.anyio
async def test_get_questions_filters_by_status(db, async_db):
    _create(db, "質問A", "回答A", status="UNREVIEWED")
    approved = _create(db, "質問B", "回答B", status="APPROVED")

    questions = await question_repository.get_questions(
        async_db, offset=0, limit=10, filters=QuestionFilters(status="APPROVED")
    )

    assert [q.id for q in questions] == [approved.id]


def test_update_content_and_status_updates_content(db):
    created = _create(db, "更新前", "更新前回答")

    updated = question_repository.update_content_and_status(
        db,
        created.id,
        status="APPROVED",
        question="更新後",
        answer="更新後回答",
    )

    assert updated.question == "更新後"
    assert updated.answer == "更新後回答"
    assert updated.status == "APPROVED"


def test_update_content_and_status_without_content_change(db):
    created = _create(db, "元の質問", "元の回答")

    updated = question_repository.update_content_and_status(
        db,
        created.id,
        status="REJECTED",
    )

    assert updated.question == "元の質問"
    assert updated.answer == "元の回答"
    assert updated.status == "REJECTED"


def test_update_content_and_status_not_found_returns_none(db):
    updated = question_repository.update_content_and_status(
        db,
        99999,
        status="APPROVED",
    )

    assert updated is None
