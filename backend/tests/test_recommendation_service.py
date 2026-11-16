import pytest

from physics_ai_tutor.schemas.question_review import QuestionReviewAction
from physics_ai_tutor.services import question_review_service, recommendation_service
from tests.conftest import (
    async_create_user,
    create_concept,
    create_embedding,
    create_question,
    link_concept,
)


def _create_question_with_embedding(db, question, answer, vector):
    q = create_question(db, question=question, answer=answer)
    db.flush()
    create_embedding(
        db,
        question_id=q.id,
        embedding=vector,
        embedding_type="question",
        model="test-model",
    )
    return q


def _create_concept(db, name, vector):
    return create_concept(
        db,
        name=name,
        embedding=vector,
        extraction_model="test-model",
        embedding_model="test-model",
        extraction_prompt_version="v1",
    )


@pytest.mark.anyio
async def test_get_related_questions_excludes_self(db, async_db):
    vector = [0.1] * 1536
    source = _create_question_with_embedding(db, "元質問", "元回答", vector)

    db.commit()
    result = (
        await recommendation_service.get_related_questions(async_db, source.id, limit=5)
    ).items

    assert source.id not in [q.id for q in result]


@pytest.mark.anyio
async def test_get_related_questions_excludes_rejected(db, async_db):
    vector = [0.1] * 1536
    source = _create_question_with_embedding(db, "元質問", "元回答", vector)
    other = _create_question_with_embedding(db, "他の質問", "他の回答", vector)
    # The review runs in its own session and only sees committed rows.
    db.commit()

    admin = await async_create_user(
        db, "rec-reviewer@example.com", "reviewerpass123", role="admin"
    )
    await question_review_service.review_question(
        async_db,
        other.id,
        action=QuestionReviewAction.REJECT,
        reviewer_id=admin.id,
    )
    db.expire_all()

    result = (
        await recommendation_service.get_related_questions(async_db, source.id, limit=5)
    ).items

    assert other.id not in [q.id for q in result]


@pytest.mark.anyio
async def test_get_related_questions_excludes_unreviewed_by_default(db, async_db):
    vector = [0.1] * 1536
    source = _create_question_with_embedding(db, "元質問", "元回答", vector)
    other = _create_question_with_embedding(db, "他の質問", "他の回答", vector)
    other.status = "UNREVIEWED"
    db.flush()

    db.commit()
    result = (
        await recommendation_service.get_related_questions(
            async_db, source.id, limit=5, exclude_statuses=["REJECTED", "UNREVIEWED"]
        )
    ).items

    assert other.id not in [q.id for q in result]


@pytest.mark.anyio
async def test_get_related_questions_includes_unreviewed_when_allowed(db, async_db):
    vector = [0.1] * 1536
    source = _create_question_with_embedding(db, "元質問", "元回答", vector)
    other = _create_question_with_embedding(db, "他の質問", "他の回答", vector)
    other.status = "UNREVIEWED"
    db.flush()

    db.commit()
    result = (
        await recommendation_service.get_related_questions(
            async_db, source.id, limit=5, exclude_statuses=["REJECTED"]
        )
    ).items

    assert other.id in [q.id for q in result]


@pytest.mark.anyio
async def test_get_related_questions_ranks_by_weighted_score(db, async_db):
    close_vector = [0.1] * 1536
    far_vector = [0.9] * 1536

    source = _create_question_with_embedding(db, "元質問", "元回答", close_vector)
    similar = _create_question_with_embedding(
        db, "似ている質問", "似ている回答", close_vector
    )
    dissimilar = _create_question_with_embedding(
        db, "似ていない質問", "似ていない回答", far_vector
    )

    db.commit()
    result = (
        await recommendation_service.get_related_questions(async_db, source.id, limit=5)
    ).items

    result_ids = [q.id for q in result]
    assert similar.id in result_ids
    assert result_ids.index(similar.id) < result_ids.index(dissimilar.id)


@pytest.mark.anyio
async def test_get_related_questions_includes_concept_sharing_candidate(db, async_db):
    vector = [0.1] * 1536
    other_vector = [-0.1] * 1536

    source = _create_question_with_embedding(db, "元質問", "元回答", vector)
    concept_sharing = _create_question_with_embedding(
        db, "概念を共有する質問", "共有回答", other_vector
    )

    concept = _create_concept(db, "共有概念", vector)
    link_concept(db, question_id=source.id, concept_id=concept.id)
    link_concept(db, question_id=concept_sharing.id, concept_id=concept.id)

    db.commit()
    result = (
        await recommendation_service.get_related_questions(async_db, source.id, limit=5)
    ).items

    assert concept_sharing.id in [q.id for q in result]


@pytest.mark.anyio
async def test_get_related_questions_returns_empty_when_no_embedding(db, async_db):
    q = create_question(db, question="埋め込みなし", answer="回答")
    db.flush()

    db.commit()
    result = (
        await recommendation_service.get_related_questions(async_db, q.id, limit=5)
    ).items

    assert result == []


@pytest.mark.anyio
async def test_get_related_questions_includes_candidate_via_rag_reference_concepts(
    db, async_db
):
    close_vector = [0.1] * 1536
    dissimilar_vector = [-0.5] * 1536

    reference = _create_question_with_embedding(
        db, "参照質問", "参照回答", close_vector
    )
    rag_question = _create_question_with_embedding(
        db, "RAG質問", "RAG回答", close_vector
    )
    rag_question.status = "UNREVIEWED"
    rag_question.retrieved_question_ids = [reference.id]
    db.flush()

    # Shares concepts only with the referenced QA: found via retrieved_question_ids.
    candidate = _create_question_with_embedding(
        db, "参照質問と概念を共有する質問", "回答", dissimilar_vector
    )

    concept = _create_concept(db, "参照経由の概念", close_vector)
    link_concept(db, question_id=reference.id, concept_id=concept.id)
    link_concept(db, question_id=candidate.id, concept_id=concept.id)

    db.commit()
    result = (
        await recommendation_service.get_related_questions(
            async_db, rag_question.id, limit=5, exclude_statuses=["REJECTED"]
        )
    ).items

    assert candidate.id in [q.id for q in result]
