import pytest

from physics_ai_tutor.core.exceptions import (
    ConceptExtractionError,
    DuplicateQuestionError,
    EmbeddingGenerationError,
)
from physics_ai_tutor.models import QuestionEmbedding
from physics_ai_tutor.repositories import question_concept_repository
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionSource,
    QuestionStatus,
    QuestionUpdate,
)
from physics_ai_tutor.schemas.question_review import QuestionReviewAction
from physics_ai_tutor.services import (
    concept_service,
    embedding_service,
    question_service,
)
from physics_ai_tutor.services.user_service import create_user


def _create(db, question: str = "テスト質問", answer: str = "テスト回答"):
    return question_service.create_question(
        db,
        QuestionCreate(question=question, answer=answer),
    )


def _embeddings_for(db, question_id: int):
    return (
        db.query(QuestionEmbedding)
        .filter(QuestionEmbedding.question_id == question_id)
        .all()
    )


def test_fetch_questions(db):
    _create(db, "質問A", "回答A")

    result = question_service.fetch_questions(db, page=1, size=20)

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].question == "質問A"


def test_fetch_questions_paginates(db):
    _create(db, "質問A", "回答A")
    _create(db, "質問B", "回答B")
    _create(db, "質問C", "回答C")

    result = question_service.fetch_questions(db, page=2, size=2)

    assert result.total == 3
    assert result.page == 2
    assert result.size == 2
    assert len(result.items) == 1


def test_fetch_questions_filters_by_keyword(db):
    matching = _create(db, "運動量保存則とは何ですか", "運動量は保存されます")
    _create(db, "エネルギー保存則とは何ですか", "エネルギーは保存されます")

    result = question_service.fetch_questions(db, page=1, size=20, keyword="運動量")

    assert result.total == 1
    assert [q.id for q in result.items] == [matching.id]


def test_fetch_questions_excludes_status(db):
    _create(db, "質問A", "回答A")
    rejected = _create(db, "質問B", "回答B")
    admin = create_user(
        db, "excl-reviewer@example.com", "reviewerpass123", role="admin"
    )
    question_service.review_question(
        db, rejected.id, action=QuestionReviewAction.REJECT, reviewer_id=admin.id,
    )

    result = question_service.fetch_questions(
        db, page=1, size=20, exclude_status=QuestionStatus.REJECTED,
    )

    remaining_ids = [q.id for q in result.items]
    assert rejected.id not in remaining_ids


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


def test_create_question_defaults_to_approved_and_manual(db):
    created = _create(db)

    assert created.status == "APPROVED"
    assert created.source == "MANUAL"


def test_create_question_duplicate_rejected(db):
    _create(db, "重複質問", "重複回答1")

    with pytest.raises(DuplicateQuestionError):
        _create(db, "重複質問", "重複回答2")

    result = question_service.fetch_questions(db, page=1, size=20)
    assert result.total == 1


def test_create_question_attaches_concepts(db):
    created = _create(db)

    concepts = question_concept_repository.get_concepts_for_question(db, created.id)

    assert {c.name for c in concepts} == {"概念A", "概念B"}


def test_create_question_concept_extraction_failure_is_non_fatal(db, monkeypatch):
    def _raise(question, answer):
        raise ConceptExtractionError("boom")

    monkeypatch.setattr(concept_service, "extract_concept_names", _raise)

    created = _create(db)

    assert created.id is not None
    assert question_concept_repository.get_concepts_for_question(db, created.id) == []


def test_import_questions_from_jsonl(db):
    created = question_service.import_questions_from_jsonl(
        db,
        [
            QuestionCreate(question="一括質問1", answer="一括回答1"),
            QuestionCreate(question="一括質問2", answer="一括回答2"),
        ],
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )

    assert len(created) == 2
    assert created[0].question == "一括質問1"
    assert created[0].status == "UNREVIEWED"
    assert created[0].source == "AI_GENERATED"


def test_import_questions_duplicate_within_batch_rejected(db):
    with pytest.raises(DuplicateQuestionError):
        question_service.import_questions_from_jsonl(
            db,
            [
                QuestionCreate(question="重複", answer="回答1"),
                QuestionCreate(question="重複", answer="回答2"),
            ],
            status=QuestionStatus.UNREVIEWED,
            source=QuestionSource.AI_GENERATED,
        )

    assert question_service.fetch_questions(db, page=1, size=20).items == []


def test_import_questions_duplicate_against_existing_rejected(db):
    _create(db, "既存質問", "既存回答")

    with pytest.raises(DuplicateQuestionError):
        question_service.import_questions_from_jsonl(
            db,
            [QuestionCreate(question="既存質問", answer="新規回答")],
            status=QuestionStatus.UNREVIEWED,
            source=QuestionSource.AI_GENERATED,
        )

    result = question_service.fetch_questions(db, page=1, size=20)
    assert result.total == 1


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

    assert question_service.fetch_questions(db, page=1, size=20).items == []


def test_create_question_creates_question_and_answer_embeddings(db):
    created = _create(db)

    embeddings = _embeddings_for(db, created.id)

    assert {e.type for e in embeddings} == {"question", "answer"}


def test_update_question_replaces_embeddings(db):
    created = _create(db, "更新前質問", "更新前回答")

    question_service.update_question(
        db,
        created.id,
        QuestionUpdate(question="更新後質問", answer="更新後回答"),
    )

    embeddings = _embeddings_for(db, created.id)

    assert len(embeddings) == 2
    assert {e.type for e in embeddings} == {"question", "answer"}


def test_update_question_rolls_back_on_embedding_failure(db, monkeypatch):
    created = _create(db, "更新前質問", "更新前回答")

    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    with pytest.raises(EmbeddingGenerationError):
        question_service.update_question(
            db,
            created.id,
            QuestionUpdate(question="更新後質問", answer="更新後回答"),
        )

    reloaded = question_service.fetch_question(db, created.id)

    assert reloaded.question == "更新前質問"
    assert reloaded.answer == "更新前回答"


def test_import_questions_creates_embeddings_for_each_question(db):
    created = question_service.import_questions_from_jsonl(
        db,
        [
            QuestionCreate(question="一括質問1", answer="一括回答1"),
            QuestionCreate(question="一括質問2", answer="一括回答2"),
        ],
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )

    for question in created:
        embeddings = _embeddings_for(db, question.id)
        assert {e.type for e in embeddings} == {"question", "answer"}


def test_import_questions_rolls_back_on_embedding_failure(db, monkeypatch):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    with pytest.raises(EmbeddingGenerationError):
        question_service.import_questions_from_jsonl(
            db,
            [QuestionCreate(question="一括質問1", answer="一括回答1")],
            status=QuestionStatus.UNREVIEWED,
            source=QuestionSource.AI_GENERATED,
        )

    assert question_service.fetch_questions(db, page=1, size=20).items == []


def test_delete_question_cascades_to_embeddings(db):
    created = _create(db)

    question_service.delete_question(db, created.id)

    assert _embeddings_for(db, created.id) == []


def test_review_question_approve(db):
    created = question_service.create_question(
        db,
        QuestionCreate(question="レビュー対象", answer="レビュー回答"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    admin = create_user(db, "reviewer1@example.com", "reviewerpass123", role="admin")

    updated = question_service.review_question(
        db, created.id, action=QuestionReviewAction.APPROVE, reviewer_id=admin.id,
    )

    assert updated.status == "APPROVED"

    reviews = question_service.fetch_question_reviews(db, created.id)
    assert len(reviews) == 1
    assert reviews[0].action == "APPROVE"
    assert reviews[0].before_question == "レビュー対象"
    assert reviews[0].after_question == "レビュー対象"


def test_review_question_reject(db):
    created = _create(db)
    admin = create_user(db, "reviewer2@example.com", "reviewerpass123", role="admin")

    updated = question_service.review_question(
        db, created.id, action=QuestionReviewAction.REJECT, reviewer_id=admin.id,
    )

    assert updated.status == "REJECTED"


def test_review_question_edit_approve_reembeds_and_records_diff(db):
    created = question_service.create_question(
        db,
        QuestionCreate(question="編集前", answer="編集前回答"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    admin = create_user(db, "reviewer3@example.com", "reviewerpass123", role="admin")

    updated = question_service.review_question(
        db,
        created.id,
        action=QuestionReviewAction.EDIT_APPROVE,
        reviewer_id=admin.id,
        question="編集後",
        answer="編集後回答",
    )

    assert updated.status == "APPROVED"
    assert updated.question == "編集後"

    embeddings = _embeddings_for(db, created.id)
    assert len(embeddings) == 2

    reviews = question_service.fetch_question_reviews(db, created.id)
    assert reviews[0].before_question == "編集前"
    assert reviews[0].after_question == "編集後"


def test_review_question_not_found_returns_none(db):
    admin = create_user(db, "reviewer4@example.com", "reviewerpass123", role="admin")

    result = question_service.review_question(
        db, 99999, action=QuestionReviewAction.APPROVE, reviewer_id=admin.id,
    )

    assert result is None
