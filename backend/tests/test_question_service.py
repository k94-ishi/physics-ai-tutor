import pytest

from physics_ai_tutor.core.exceptions import (
    ConceptExtractionError,
    DuplicateQuestionError,
    EmbeddingGenerationError,
)
from physics_ai_tutor.models import QuestionEmbedding
from physics_ai_tutor.repositories import (
    question_concept_repository,
    question_repository,
)
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


def _spy_extract_concept_names(monkeypatch, calls):
    def _fake(question, answer):
        calls.append((question, answer))
        return ["概念A", "概念B"]

    monkeypatch.setattr(concept_service, "extract_concept_names", _fake)


def test_create_question_unreviewed_skips_concept_extraction(db, monkeypatch):
    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    created = question_service.create_question(
        db,
        QuestionCreate(question="質問", answer="回答"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )

    assert calls == []
    assert question_concept_repository.get_concepts_for_question(db, created.id) == []


def test_create_question_approved_extracts_concepts(db, monkeypatch):
    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    created = _create(db)

    assert len(calls) == 1
    assert question_concept_repository.get_concepts_for_question(db, created.id) != []


def test_import_questions_unreviewed_skips_concept_extraction(db, monkeypatch):
    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    created = question_service.import_questions_from_jsonl(
        db,
        [QuestionCreate(question="一括質問1", answer="一括回答1")],
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )

    assert calls == []
    assert (
        question_concept_repository.get_concepts_for_question(db, created[0].id) == []
    )


def test_import_questions_approved_extracts_concepts(db, monkeypatch):
    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    created = question_service.import_questions_from_jsonl(
        db,
        [
            QuestionCreate(question="一括質問1", answer="一括回答1"),
            QuestionCreate(question="一括質問2", answer="一括回答2"),
        ],
        status=QuestionStatus.APPROVED,
        source=QuestionSource.MANUAL,
    )

    assert len(calls) == 2
    for question in created:
        assert question_concept_repository.get_concepts_for_question(
            db, question.id
        ) != []


def test_review_question_approve_extracts_concepts(db, monkeypatch):
    created = question_service.create_question(
        db,
        QuestionCreate(question="レビュー対象", answer="レビュー回答"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    admin = create_user(
        db, "extract-approve@example.com", "reviewerpass123", role="admin"
    )

    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    question_service.review_question(
        db, created.id, action=QuestionReviewAction.APPROVE, reviewer_id=admin.id,
    )

    assert len(calls) == 1
    assert question_concept_repository.get_concepts_for_question(db, created.id) != []


def test_review_question_reject_does_not_extract_concepts(db, monkeypatch):
    created = _create(db)
    admin = create_user(
        db, "extract-reject@example.com", "reviewerpass123", role="admin"
    )

    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    question_service.review_question(
        db, created.id, action=QuestionReviewAction.REJECT, reviewer_id=admin.id,
    )

    assert calls == []


def test_review_question_edit_approve_extracts_from_updated_content(db, monkeypatch):
    created = question_service.create_question(
        db,
        QuestionCreate(question="編集前", answer="編集前回答"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    admin = create_user(db, "extract-edit@example.com", "reviewerpass123", role="admin")

    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    question_service.review_question(
        db,
        created.id,
        action=QuestionReviewAction.EDIT_APPROVE,
        reviewer_id=admin.id,
        question="編集後",
        answer="編集後回答",
    )

    assert calls == [("編集後", "編集後回答")]


def test_fetch_questions_includes_concepts(db):
    created = _create(db)

    result = question_service.fetch_questions(db, page=1, size=20)

    assert result.items[0].concepts == ["概念A", "概念B"]
    assert created.id == result.items[0].id


def test_fetch_question_includes_concepts(db):
    created = _create(db)

    found = question_service.fetch_question(db, created.id)

    assert found.concepts == ["概念A", "概念B"]


def test_save_ai_question_success(db):
    saved = question_service.save_ai_question(db, "AIへの質問", "AIの回答")

    assert saved is not None
    assert saved.status == "UNREVIEWED"
    assert saved.source == "AI_GENERATED"
    assert saved.language == "ja"
    assert _embeddings_for(db, saved.id) != []


def test_save_ai_question_does_not_extract_concepts(db, monkeypatch):
    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    saved = question_service.save_ai_question(db, "AIへの質問2", "AIの回答2")

    assert calls == []
    assert question_concept_repository.get_concepts_for_question(db, saved.id) == []


def test_save_ai_question_duplicate_returns_none(db):
    _create(db, "既にある質問", "既にある回答")

    saved = question_service.save_ai_question(db, "既にある質問", "別の回答")

    assert saved is None


def test_save_ai_question_embedding_failure_returns_none(db, monkeypatch):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    monkeypatch.setattr(embedding_service, "create_embeddings", _raise)

    saved = question_service.save_ai_question(db, "失敗する質問", "失敗する回答")

    assert saved is None
    assert question_service.fetch_questions(db, page=1, size=20).items == []


def test_bulk_delete_questions(db):
    q1 = _create(db, "質問1", "回答1")
    q2 = _create(db, "質問2", "回答2")

    deleted_count, not_found_ids = question_service.bulk_delete_questions(
        db, [q1.id, q2.id, 99999]
    )

    assert deleted_count == 2
    assert not_found_ids == [99999]
    assert question_service.fetch_questions(db, page=1, size=20).total == 0


def test_bulk_review_questions_approve(db):
    q1 = question_service.create_question(
        db, QuestionCreate(question="質問1", answer="回答1"),
        status=QuestionStatus.UNREVIEWED, source=QuestionSource.AI_GENERATED,
    )
    q2 = question_service.create_question(
        db, QuestionCreate(question="質問2", answer="回答2"),
        status=QuestionStatus.UNREVIEWED, source=QuestionSource.AI_GENERATED,
    )
    admin = create_user(db, "bulk-approve@example.com", "reviewerpass123", role="admin")

    updated, not_found_ids = question_service.bulk_review_questions(
        db, [q1.id, q2.id, 99999], action=QuestionReviewAction.APPROVE,
        reviewer_id=admin.id,
    )

    assert {q.status for q in updated} == {"APPROVED"}
    assert len(updated) == 2
    assert not_found_ids == [99999]


def test_bulk_review_questions_reject(db):
    q1 = _create(db, "質問1", "回答1")
    admin = create_user(db, "bulk-reject@example.com", "reviewerpass123", role="admin")

    updated, not_found_ids = question_service.bulk_review_questions(
        db, [q1.id], action=QuestionReviewAction.REJECT, reviewer_id=admin.id,
    )

    assert updated[0].status == "REJECTED"
    assert not_found_ids == []


def test_reextract_concepts_for_questions_replaces_existing_links(db, monkeypatch):
    created = _create(db)
    assert question_concept_repository.get_concepts_for_question(db, created.id) != []

    monkeypatch.setattr(
        concept_service,
        "extract_concept_names",
        lambda question, answer: ["新概念"],
    )

    results = question_service.reextract_concepts_for_questions(db, [created.id])

    assert results[0].success is True
    assert results[0].concepts == ["新概念"]
    concepts = question_concept_repository.get_concepts_for_question(db, created.id)
    assert [c.name for c in concepts] == ["新概念"]


def test_reextract_concepts_for_questions_not_found(db):
    results = question_service.reextract_concepts_for_questions(db, [99999])

    assert len(results) == 1
    assert results[0].question_id == 99999
    assert results[0].success is False


def test_reextract_concepts_for_questions_partial_failure_continues(db, monkeypatch):
    q1 = _create(db, "質問1", "回答1")
    q2 = _create(db, "質問2", "回答2")

    def _fake(question, answer):
        if question == "質問1":
            raise ConceptExtractionError("boom")
        return ["概念X"]

    monkeypatch.setattr(concept_service, "extract_concept_names", _fake)

    results = question_service.reextract_concepts_for_questions(db, [q1.id, q2.id])

    results_by_id = {r.question_id: r for r in results}
    assert results_by_id[q1.id].success is False
    assert results_by_id[q2.id].success is True
    assert question_concept_repository.get_concepts_for_question(db, q2.id) != []


def test_attach_retrieved_questions_resolves_ids_to_summaries(db):
    referenced1 = question_repository.create_question(
        db, question="参照質問1", answer="回答1"
    )
    referenced2 = question_repository.create_question(
        db, question="参照質問2", answer="回答2"
    )
    rag_question = question_repository.create_question(
        db,
        question="RAG質問",
        answer="RAG回答",
        retrieved_question_ids=[referenced1.id, referenced2.id],
    )

    question_service.attach_retrieved_questions(db, [rag_question])

    assert rag_question.retrieved_questions == [
        {"id": referenced1.id, "question": "参照質問1"},
        {"id": referenced2.id, "question": "参照質問2"},
    ]


def test_attach_retrieved_questions_skips_missing_ids(db):
    rag_question = question_repository.create_question(
        db, question="RAG質問", answer="RAG回答", retrieved_question_ids=[999999]
    )

    question_service.attach_retrieved_questions(db, [rag_question])

    assert rag_question.retrieved_questions == []


def test_attach_retrieved_questions_empty_for_normal_questions(db):
    question = _create(db)

    question_service.attach_retrieved_questions(db, [question])

    assert question.retrieved_questions == []
