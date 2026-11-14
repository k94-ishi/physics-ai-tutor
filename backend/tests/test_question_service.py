import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.core.exceptions import (
    ConceptExtractionError,
    DuplicateQuestionError,
    EmbeddingGenerationError,
)
from physics_ai_tutor.models import Question, QuestionEmbedding
from physics_ai_tutor.repositories import (
    question_concept_repository,
    question_repository,
)
from physics_ai_tutor.schemas.question import (
    QuestionCreate,
    QuestionFilters,
    QuestionSource,
    QuestionStatus,
    QuestionUpdate,
)
from physics_ai_tutor.schemas.question_review import QuestionReviewAction
from physics_ai_tutor.services import (
    question_presentation_service,
    question_read_service,
    question_review_service,
    question_write_service,
)
from tests.conftest import (
    async_create_user,
    async_engine,
    patch_create_embeddings,
    patch_extract_concept_names,
)


async def _created_id(data: QuestionCreate, **kwargs) -> int:
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        created = await question_write_service.create_question(session, data, **kwargs)
        return created.id


def _create_row(db, data: QuestionCreate, **kwargs) -> Question:
    """Create through the async service from a sync test ([93])."""
    return db.get(Question, asyncio.run(_created_id(data, **kwargs)))


async def _acreate_row(db, data: QuestionCreate, **kwargs) -> Question:
    """`_create_row` for a test already on the event loop."""
    return db.get(Question, await _created_id(data, **kwargs))


def _create(db, question: str = "テスト質問", answer: str = "テスト回答"):
    return _create_row(db, QuestionCreate(question=question, answer=answer))


async def _acreate(db, question: str = "テスト質問", answer: str = "テスト回答"):
    return await _acreate_row(db, QuestionCreate(question=question, answer=answer))


def _embeddings_for(db, question_id: int, language: str = "ja"):
    # Rows are embedded per language; tests inspect one language at a time.
    return (
        db.query(QuestionEmbedding)
        .filter(
            QuestionEmbedding.question_id == question_id,
            QuestionEmbedding.language == language,
        )
        .all()
    )


@pytest.mark.anyio
async def test_fetch_questions(db, async_db):
    await _acreate(db, "質問A", "回答A")

    result = await question_read_service.fetch_questions(async_db, page=1, size=20)

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].question == "質問A"


@pytest.mark.anyio
async def test_fetch_questions_paginates(db, async_db):
    await _acreate(db, "質問A", "回答A")
    await _acreate(db, "質問B", "回答B")
    await _acreate(db, "質問C", "回答C")

    result = await question_read_service.fetch_questions(async_db, page=2, size=2)

    assert result.total == 3
    assert result.page == 2
    assert result.size == 2
    assert len(result.items) == 1


@pytest.mark.anyio
async def test_fetch_questions_filters_by_keyword(db, async_db):
    matching = await _acreate(db, "運動量保存則とは何ですか", "運動量は保存されます")
    await _acreate(db, "エネルギー保存則とは何ですか", "エネルギーは保存されます")

    result = await question_read_service.fetch_questions(
        async_db, page=1, size=20, filters=QuestionFilters(keyword="運動量")
    )

    assert result.total == 1
    assert [q.id for q in result.items] == [matching.id]


@pytest.mark.anyio
async def test_fetch_questions_excludes_status(db, async_db):
    await _acreate(db, "質問A", "回答A")
    rejected = await _acreate(db, "質問B", "回答B")
    admin = await async_create_user(
        db, "excl-reviewer@example.com", "reviewerpass123", role="admin"
    )
    await question_review_service.review_question(
        async_db,
        rejected.id,
        action=QuestionReviewAction.REJECT,
        reviewer_id=admin.id,
    )
    db.expire_all()

    result = await question_read_service.fetch_questions(
        async_db,
        page=1,
        size=20,
        filters=QuestionFilters(exclude_statuses=[QuestionStatus.REJECTED]),
    )

    remaining_ids = [q.id for q in result.items]
    assert rejected.id not in remaining_ids


@pytest.mark.anyio
async def test_fetch_question_found(db, async_db):
    created = await _acreate(db)

    found = (await question_read_service.fetch_question(async_db, created.id))[0]

    assert found is not None
    assert found.id == created.id


@pytest.mark.anyio
async def test_fetch_question_not_found(db, async_db):
    found = (await question_read_service.fetch_question(async_db, 99999))[0]

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


@pytest.mark.anyio
async def test_create_question_duplicate_rejected(db, async_db):
    await _acreate(db, "重複質問", "重複回答1")

    with pytest.raises(DuplicateQuestionError):
        await _acreate(db, "重複質問", "重複回答2")

    result = await question_read_service.fetch_questions(async_db, page=1, size=20)
    assert result.total == 1


def test_create_question_attaches_concepts(db):
    created = _create(db)

    concepts = question_concept_repository.get_concepts_for_question(db, created.id)

    assert {c.name for c in concepts} == {"概念A", "概念B"}


def test_create_question_concept_extraction_failure_is_non_fatal(db, monkeypatch):
    def _raise(question, answer, language="ja"):
        raise ConceptExtractionError("boom")

    patch_extract_concept_names(monkeypatch, _raise)

    created = _create(db)

    assert created.id is not None
    assert question_concept_repository.get_concepts_for_question(db, created.id) == []


def test_import_questions_from_jsonl(db):
    created = question_write_service.import_questions_from_jsonl(
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


@pytest.mark.anyio
async def test_import_questions_duplicate_within_batch_rejected(db, async_db):
    with pytest.raises(DuplicateQuestionError):
        question_write_service.import_questions_from_jsonl(
            db,
            [
                QuestionCreate(question="重複", answer="回答1"),
                QuestionCreate(question="重複", answer="回答2"),
            ],
            status=QuestionStatus.UNREVIEWED,
            source=QuestionSource.AI_GENERATED,
        )

    assert (
        await question_read_service.fetch_questions(async_db, page=1, size=20)
    ).items == []


@pytest.mark.anyio
async def test_import_questions_duplicate_against_existing_rejected(db, async_db):
    await _acreate(db, "既存質問", "既存回答")

    with pytest.raises(DuplicateQuestionError):
        question_write_service.import_questions_from_jsonl(
            db,
            [QuestionCreate(question="既存質問", answer="新規回答")],
            status=QuestionStatus.UNREVIEWED,
            source=QuestionSource.AI_GENERATED,
        )

    result = await question_read_service.fetch_questions(async_db, page=1, size=20)
    assert result.total == 1


@pytest.mark.anyio
async def test_delete_question_existing_returns_true(db, async_db):
    created = await _acreate(db)

    # Read before the delete: the row is gone afterwards.
    created_id = created.id
    result = await question_write_service.delete_question(async_db, created_id)

    db.expire_all()

    assert result is True
    assert (await question_read_service.fetch_question(async_db, created_id))[0] is None


@pytest.mark.anyio
async def test_delete_question_not_found_returns_false(db, async_db):
    result = await question_write_service.delete_question(async_db, 99999)
    db.expire_all()

    assert result is False


@pytest.mark.anyio
async def test_update_question_existing(db, async_db):
    created = await _acreate(db, "更新前質問", "更新前回答")

    updated = await question_write_service.update_question(
        async_db,
        created.id,
        QuestionUpdate(question="更新後質問", answer="更新後回答"),
    )

    db.expire_all()

    assert updated is not None
    assert updated.question == "更新後質問"


@pytest.mark.anyio
async def test_update_question_not_found_returns_none(db, async_db):
    updated = await question_write_service.update_question(
        async_db,
        99999,
        QuestionUpdate(question="更新後質問", answer="更新後回答"),
    )
    db.expire_all()

    assert updated is None


@pytest.mark.anyio
async def test_create_question_rolls_back_on_embedding_failure(
    db, async_db, monkeypatch
):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    patch_create_embeddings(monkeypatch, _raise)

    with pytest.raises(EmbeddingGenerationError):
        await _acreate(db)

    assert (
        await question_read_service.fetch_questions(async_db, page=1, size=20)
    ).items == []


def test_create_question_creates_question_and_answer_embeddings(db):
    created = _create(db)

    embeddings = _embeddings_for(db, created.id)

    assert {e.type for e in embeddings} == {"question", "answer"}


@pytest.mark.anyio
async def test_update_question_replaces_embeddings(db, async_db):
    created = await _acreate(db, "更新前質問", "更新前回答")

    await question_write_service.update_question(
        async_db,
        created.id,
        QuestionUpdate(question="更新後質問", answer="更新後回答"),
    )

    db.expire_all()

    embeddings = _embeddings_for(db, created.id)

    assert len(embeddings) == 2
    assert {e.type for e in embeddings} == {"question", "answer"}


@pytest.mark.anyio
async def test_update_question_rolls_back_on_embedding_failure(
    db, async_db, monkeypatch
):
    created = await _acreate(db, "更新前質問", "更新前回答")

    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    patch_create_embeddings(monkeypatch, _raise)

    with pytest.raises(EmbeddingGenerationError):
        await question_write_service.update_question(
            async_db,
            created.id,
            QuestionUpdate(question="更新後質問", answer="更新後回答"),
        )

    reloaded = (await question_read_service.fetch_question(async_db, created.id))[0]

    assert reloaded.question == "更新前質問"
    assert reloaded.answer == "更新前回答"


def test_import_questions_creates_embeddings_for_each_question(db):
    created = question_write_service.import_questions_from_jsonl(
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


@pytest.mark.anyio
async def test_import_questions_rolls_back_on_embedding_failure(
    db, async_db, monkeypatch
):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    patch_create_embeddings(monkeypatch, _raise)

    with pytest.raises(EmbeddingGenerationError):
        question_write_service.import_questions_from_jsonl(
            db,
            [QuestionCreate(question="一括質問1", answer="一括回答1")],
            status=QuestionStatus.UNREVIEWED,
            source=QuestionSource.AI_GENERATED,
        )

    assert (
        await question_read_service.fetch_questions(async_db, page=1, size=20)
    ).items == []


@pytest.mark.anyio
async def test_delete_question_cascades_to_embeddings(db, async_db):
    created = await _acreate(db)

    # Read before the delete: the row is gone afterwards.
    created_id = created.id
    await question_write_service.delete_question(async_db, created_id)

    db.expire_all()

    assert _embeddings_for(db, created_id) == []


@pytest.mark.anyio
async def test_review_question_approve(db, async_db):
    created = await _acreate_row(
        db,
        QuestionCreate(question="レビュー対象", answer="レビュー回答"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    admin = await async_create_user(
        db, "reviewer1@example.com", "reviewerpass123", role="admin"
    )

    updated = await question_review_service.review_question(
        async_db,
        created.id,
        action=QuestionReviewAction.APPROVE,
        reviewer_id=admin.id,
    )

    db.expire_all()

    assert updated.status == "APPROVED"

    reviews = await question_review_service.fetch_question_reviews(async_db, created.id)
    assert len(reviews) == 1
    assert reviews[0].action == "APPROVE"
    assert reviews[0].before_question == "レビュー対象"
    assert reviews[0].after_question == "レビュー対象"


@pytest.mark.anyio
async def test_review_question_reject(db, async_db):
    created = await _acreate(db)
    admin = await async_create_user(
        db, "reviewer2@example.com", "reviewerpass123", role="admin"
    )

    updated = await question_review_service.review_question(
        async_db,
        created.id,
        action=QuestionReviewAction.REJECT,
        reviewer_id=admin.id,
    )

    db.expire_all()

    assert updated.status == "REJECTED"


@pytest.mark.anyio
async def test_review_question_edit_approve_reembeds_and_records_diff(db, async_db):
    created = await _acreate_row(
        db,
        QuestionCreate(question="編集前", answer="編集前回答"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    admin = await async_create_user(
        db, "reviewer3@example.com", "reviewerpass123", role="admin"
    )

    updated = await question_review_service.review_question(
        async_db,
        created.id,
        action=QuestionReviewAction.EDIT_APPROVE,
        reviewer_id=admin.id,
        question="編集後",
        answer="編集後回答",
    )

    db.expire_all()

    assert updated.status == "APPROVED"
    assert updated.question == "編集後"

    embeddings = _embeddings_for(db, created.id)
    assert len(embeddings) == 2

    reviews = await question_review_service.fetch_question_reviews(async_db, created.id)
    assert reviews[0].before_question == "編集前"
    assert reviews[0].after_question == "編集後"


@pytest.mark.anyio
async def test_edit_approve_embedding_failure_writes_nothing(db, async_db, monkeypatch):
    """The AI phase works on a draft, so a failure leaves no trace ([85])."""
    created = await _acreate_row(
        db,
        QuestionCreate(question="元の質問", answer="元の回答"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    admin = await async_create_user(
        db, "edit-fail@example.com", "reviewerpass123", role="admin"
    )

    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    patch_create_embeddings(monkeypatch, _raise)

    with pytest.raises(EmbeddingGenerationError):
        await question_review_service.review_question(
            async_db,
            created.id,
            action=QuestionReviewAction.EDIT_APPROVE,
            reviewer_id=admin.id,
            question="編集後",
            answer="編集後回答",
            reason="PHYSICS_ERROR",
        )
    # The same session must still be clean for the next item of a bulk run.
    assert not async_db.dirty

    db.expire_all()
    row = question_repository.get_question(db, created.id)
    assert (row.question, row.status) == ("元の質問", QuestionStatus.UNREVIEWED)
    history = await question_review_service.fetch_question_reviews(async_db, created.id)
    assert history == []


@pytest.mark.anyio
async def test_review_question_not_found_returns_none(db, async_db):
    admin = await async_create_user(
        db, "reviewer4@example.com", "reviewerpass123", role="admin"
    )

    result = await question_review_service.review_question(
        async_db,
        99999,
        action=QuestionReviewAction.APPROVE,
        reviewer_id=admin.id,
    )

    db.expire_all()

    assert result is None


def _spy_extract_concept_names(monkeypatch, calls):
    def _fake(question, answer, language="ja"):
        calls.append((question, answer))
        return ["概念A", "概念B"]

    patch_extract_concept_names(monkeypatch, _fake)


def test_create_question_unreviewed_skips_concept_extraction(db, monkeypatch):
    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    created = _create_row(
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

    created = question_write_service.import_questions_from_jsonl(
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

    created = question_write_service.import_questions_from_jsonl(
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
        assert (
            question_concept_repository.get_concepts_for_question(db, question.id) != []
        )


@pytest.mark.anyio
async def test_review_question_approve_extracts_concepts(db, async_db, monkeypatch):
    created = await _acreate_row(
        db,
        QuestionCreate(question="レビュー対象", answer="レビュー回答"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    admin = await async_create_user(
        db, "extract-approve@example.com", "reviewerpass123", role="admin"
    )

    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    await question_review_service.review_question(
        async_db,
        created.id,
        action=QuestionReviewAction.APPROVE,
        reviewer_id=admin.id,
    )

    db.expire_all()

    assert len(calls) == 1
    assert question_concept_repository.get_concepts_for_question(db, created.id) != []


@pytest.mark.anyio
async def test_review_question_reject_does_not_extract_concepts(
    db, async_db, monkeypatch
):
    created = await _acreate(db)
    admin = await async_create_user(
        db, "extract-reject@example.com", "reviewerpass123", role="admin"
    )

    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    await question_review_service.review_question(
        async_db,
        created.id,
        action=QuestionReviewAction.REJECT,
        reviewer_id=admin.id,
    )

    db.expire_all()

    assert calls == []


@pytest.mark.anyio
async def test_review_question_edit_approve_extracts_from_updated_content(
    db, async_db, monkeypatch
):
    created = await _acreate_row(
        db,
        QuestionCreate(question="編集前", answer="編集前回答"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    admin = await async_create_user(
        db, "extract-edit@example.com", "reviewerpass123", role="admin"
    )

    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    await question_review_service.review_question(
        async_db,
        created.id,
        action=QuestionReviewAction.EDIT_APPROVE,
        reviewer_id=admin.id,
        question="編集後",
        answer="編集後回答",
    )

    db.expire_all()

    assert calls == [("編集後", "編集後回答")]


@pytest.mark.anyio
async def test_fetch_questions_includes_concepts(db, async_db):
    created = await _acreate(db)

    result = await question_read_service.fetch_questions(async_db, page=1, size=20)

    assert result.items[0].concepts == ["概念A", "概念B"]
    assert created.id == result.items[0].id


@pytest.mark.anyio
async def test_fetch_question_includes_concepts(db, async_db):
    created = await _acreate(db)

    found = (await question_read_service.fetch_question(async_db, created.id))[0]

    assert found.concepts == ["概念A", "概念B"]


@pytest.mark.anyio
async def test_save_ai_question_success(db, async_db):
    saved = await question_write_service.async_save_ai_question(
        async_db, "AIへの質問", "AIの回答"
    )

    assert saved is not None
    assert saved.status == "UNREVIEWED"
    assert saved.source == "AI_GENERATED"
    assert saved.language == "ja"
    assert _embeddings_for(db, saved.id) != []


@pytest.mark.anyio
async def test_save_ai_question_does_not_extract_concepts(db, async_db, monkeypatch):
    calls = []
    _spy_extract_concept_names(monkeypatch, calls)

    saved = await question_write_service.async_save_ai_question(
        async_db, "AIへの質問2", "AIの回答2"
    )

    assert calls == []
    assert question_concept_repository.get_concepts_for_question(db, saved.id) == []


@pytest.mark.anyio
async def test_save_ai_question_duplicate_returns_none(db, async_db):
    await _acreate(db, "既にある質問", "既にある回答")
    db.commit()

    saved = await question_write_service.async_save_ai_question(
        async_db, "既にある質問", "別の回答"
    )

    assert saved is None


@pytest.mark.anyio
async def test_save_ai_question_embedding_failure_returns_none(
    db, async_db, monkeypatch
):
    def _raise(texts):
        raise EmbeddingGenerationError("boom")

    patch_create_embeddings(monkeypatch, _raise)

    saved = await question_write_service.async_save_ai_question(
        async_db, "失敗する質問", "失敗する回答"
    )

    assert saved is None
    assert (
        await question_read_service.fetch_questions(async_db, page=1, size=20)
    ).items == []


@pytest.mark.anyio
async def test_bulk_delete_questions(db, async_db):
    q1 = await _acreate(db, "質問1", "回答1")
    q2 = await _acreate(db, "質問2", "回答2")

    deleted_count, not_found_ids = await question_write_service.bulk_delete_questions(
        async_db, [q1.id, q2.id, 99999]
    )

    db.expire_all()

    assert deleted_count == 2
    assert not_found_ids == [99999]
    assert (
        await question_read_service.fetch_questions(async_db, page=1, size=20)
    ).total == 0


@pytest.mark.anyio
async def test_bulk_review_questions_approve(db, async_db):
    q1 = await _acreate_row(
        db,
        QuestionCreate(question="質問1", answer="回答1"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    q2 = await _acreate_row(
        db,
        QuestionCreate(question="質問2", answer="回答2"),
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    admin = await async_create_user(
        db, "bulk-approve@example.com", "reviewerpass123", role="admin"
    )

    updated, not_found_ids = await question_review_service.bulk_review_questions(
        async_db,
        [q1.id, q2.id, 99999],
        action=QuestionReviewAction.APPROVE,
        reviewer_id=admin.id,
    )

    db.expire_all()

    assert {q.status for q in updated} == {"APPROVED"}
    assert len(updated) == 2
    assert not_found_ids == [99999]


@pytest.mark.anyio
async def test_bulk_review_questions_reject(db, async_db):
    q1 = await _acreate(db, "質問1", "回答1")
    admin = await async_create_user(
        db, "bulk-reject@example.com", "reviewerpass123", role="admin"
    )

    updated, not_found_ids = await question_review_service.bulk_review_questions(
        async_db,
        [q1.id],
        action=QuestionReviewAction.REJECT,
        reviewer_id=admin.id,
    )

    db.expire_all()

    assert updated[0].status == "REJECTED"
    assert not_found_ids == []


@pytest.mark.anyio
async def test_reextract_concepts_for_questions_replaces_existing_links(
    db, async_db, monkeypatch
):
    created = await _acreate(db)
    assert question_concept_repository.get_concepts_for_question(db, created.id) != []

    patch_extract_concept_names(
        monkeypatch, lambda question, answer, language="ja": ["新概念"]
    )

    results = await question_write_service.reextract_concepts_for_questions(
        async_db, [created.id]
    )

    assert results[0].success is True
    assert results[0].concepts == ["新概念"]
    db.expire_all()
    concepts = question_concept_repository.get_concepts_for_question(db, created.id)
    assert [c.name for c in concepts] == ["新概念"]


@pytest.mark.anyio
async def test_reextract_concepts_for_questions_not_found(async_db):
    results = await question_write_service.reextract_concepts_for_questions(
        async_db, [99999]
    )

    assert len(results) == 1
    assert results[0].question_id == 99999
    assert results[0].success is False


@pytest.mark.anyio
async def test_reextract_concepts_for_questions_partial_failure_continues(
    db, async_db, monkeypatch
):
    q1 = await _acreate(db, "質問1", "回答1")
    q2 = await _acreate(db, "質問2", "回答2")

    def _fake(question, answer, language="ja"):
        if question == "質問1":
            raise ConceptExtractionError("boom")
        return ["概念X"]

    patch_extract_concept_names(monkeypatch, _fake)

    results = await question_write_service.reextract_concepts_for_questions(
        async_db, [q1.id, q2.id]
    )

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

    question_presentation_service.attach_retrieved_questions(db, [rag_question])

    assert rag_question.retrieved_questions == [
        {"id": referenced1.id, "question": "参照質問1"},
        {"id": referenced2.id, "question": "参照質問2"},
    ]


def test_attach_retrieved_questions_skips_missing_ids(db):
    rag_question = question_repository.create_question(
        db, question="RAG質問", answer="RAG回答", retrieved_question_ids=[999999]
    )

    question_presentation_service.attach_retrieved_questions(db, [rag_question])

    assert rag_question.retrieved_questions == []


def test_attach_retrieved_questions_empty_for_normal_questions(db):
    question = _create(db)

    question_presentation_service.attach_retrieved_questions(db, [question])

    assert question.retrieved_questions == []
