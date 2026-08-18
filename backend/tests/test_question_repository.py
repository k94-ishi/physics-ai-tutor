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


def test_get_questions_respects_offset_and_limit(db):
    _create(db, "質問A", "回答A")
    _create(db, "質問B", "回答B")
    _create(db, "質問C", "回答C")

    questions = question_repository.get_questions(db, offset=1, limit=1)

    assert len(questions) == 1


def test_count_questions_returns_total(db):
    _create(db, "質問A", "回答A")
    _create(db, "質問B", "回答B")

    assert question_repository.count_questions(db) == 2


def test_get_questions_filters_by_keyword_in_question(db):
    matching = _create(db, "運動量保存則とは何ですか", "運動量は保存されます")
    _create(db, "エネルギー保存則とは何ですか", "エネルギーは保存されます")

    questions = question_repository.get_questions(
        db, offset=0, limit=10, keyword="運動量"
    )

    assert [q.id for q in questions] == [matching.id]


def test_get_questions_filters_by_keyword_in_answer(db):
    matching = _create(db, "第一法則とは", "運動量は保存されます")
    _create(db, "第二法則とは", "力は質量と加速度の積です")

    questions = question_repository.get_questions(
        db, offset=0, limit=10, keyword="運動量"
    )

    assert [q.id for q in questions] == [matching.id]


def test_count_questions_filters_by_keyword(db):
    _create(db, "運動量保存則とは何ですか", "運動量は保存されます")
    _create(db, "エネルギー保存則とは何ですか", "エネルギーは保存されます")

    assert question_repository.count_questions(db, keyword="運動量") == 1


def test_get_questions_keyword_no_match_returns_empty(db):
    _create(db, "運動量保存則とは何ですか", "運動量は保存されます")

    questions = question_repository.get_questions(
        db, offset=0, limit=10, keyword="存在しないキーワード"
    )

    assert questions == []


def test_get_questions_keyword_and_across_terms(db):
    matching = _create(
        db, "運動量保存則とは何ですか", "衝突の前後で運動量は保存されます"
    )
    _create(db, "運動量保存則とは何ですか", "エネルギーは保存されます")
    _create(db, "衝突とは何ですか", "衝突の説明です")

    questions = question_repository.get_questions(
        db, offset=0, limit=10, keyword="運動量 衝突"
    )

    assert [q.id for q in questions] == [matching.id]


def test_get_questions_keyword_search_question_only(db):
    matching = _create(db, "運動量保存則とは何ですか", "回答")
    _create(db, "第一法則とは", "運動量は保存されます")

    questions = question_repository.get_questions(
        db,
        offset=0,
        limit=10,
        keyword="運動量",
        search_question=True,
        search_answer=False,
    )

    assert [q.id for q in questions] == [matching.id]


def test_get_questions_keyword_search_answer_only(db):
    _create(db, "運動量保存則とは何ですか", "回答")
    matching = _create(db, "第一法則とは", "運動量は保存されます")

    questions = question_repository.get_questions(
        db,
        offset=0,
        limit=10,
        keyword="運動量",
        search_question=False,
        search_answer=True,
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
        db, "却下済み質問", exclude_status="REJECTED"
    )

    assert found is None


def test_get_by_exact_text_includes_unreviewed_by_default(db):
    created = question_repository.create_question(
        db, question="未レビュー質問", answer="回答", status="UNREVIEWED"
    )

    found = question_repository.get_by_exact_text(
        db, "未レビュー質問", exclude_status="REJECTED"
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


def test_get_questions_excludes_status(db):
    _create(db, "質問A", "回答A")
    rejected = question_repository.create_question(
        db,
        question="質問B",
        answer="回答B",
        status="REJECTED",
    )

    questions = question_repository.get_questions(
        db,
        offset=0,
        limit=10,
        exclude_status="REJECTED",
    )

    assert rejected.id not in [q.id for q in questions]


def test_get_questions_filters_by_status(db):
    question_repository.create_question(
        db,
        question="質問A",
        answer="回答A",
        status="UNREVIEWED",
    )
    approved = question_repository.create_question(
        db,
        question="質問B",
        answer="回答B",
        status="APPROVED",
    )

    questions = question_repository.get_questions(
        db,
        offset=0,
        limit=10,
        status="APPROVED",
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
