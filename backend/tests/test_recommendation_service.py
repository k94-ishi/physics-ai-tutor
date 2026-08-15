from physics_ai_tutor.repositories import (
    concept_repository,
    embedding_repository,
    question_concept_repository,
    question_repository,
)
from physics_ai_tutor.schemas.question_review import QuestionReviewAction
from physics_ai_tutor.services import question_service, recommendation_service
from physics_ai_tutor.services.user_service import create_user


def _create_question_with_embedding(db, question, answer, vector):
    q = question_repository.create_question(db, question=question, answer=answer)
    db.flush()
    embedding_repository.create_embedding(
        db,
        question_id=q.id,
        embedding=vector,
        embedding_type="question",
        model="test-model",
    )
    return q


def _create_concept(db, name, vector):
    return concept_repository.create(
        db,
        name=name,
        embedding=vector,
        extraction_model="test-model",
        embedding_model="test-model",
        extraction_prompt_version="v1",
    )


def test_get_related_questions_excludes_self(db):
    vector = [0.1] * 1536
    source = _create_question_with_embedding(db, "元質問", "元回答", vector)

    result = recommendation_service.get_related_questions(db, source.id, limit=5)

    assert source.id not in [q.id for q in result]


def test_get_related_questions_excludes_rejected(db):
    vector = [0.1] * 1536
    source = _create_question_with_embedding(db, "元質問", "元回答", vector)
    other = _create_question_with_embedding(db, "他の質問", "他の回答", vector)

    admin = create_user(db, "rec-reviewer@example.com", "reviewerpass123", role="admin")
    question_service.review_question(
        db, other.id, action=QuestionReviewAction.REJECT, reviewer_id=admin.id,
    )

    result = recommendation_service.get_related_questions(db, source.id, limit=5)

    assert other.id not in [q.id for q in result]


def test_get_related_questions_excludes_unreviewed_by_default(db):
    vector = [0.1] * 1536
    source = _create_question_with_embedding(db, "元質問", "元回答", vector)
    other = _create_question_with_embedding(db, "他の質問", "他の回答", vector)
    question_repository.update_content_and_status(db, other.id, status="UNREVIEWED")

    result = recommendation_service.get_related_questions(
        db, source.id, limit=5, exclude_statuses=["REJECTED", "UNREVIEWED"]
    )

    assert other.id not in [q.id for q in result]


def test_get_related_questions_includes_unreviewed_when_allowed(db):
    vector = [0.1] * 1536
    source = _create_question_with_embedding(db, "元質問", "元回答", vector)
    other = _create_question_with_embedding(db, "他の質問", "他の回答", vector)
    question_repository.update_content_and_status(db, other.id, status="UNREVIEWED")

    result = recommendation_service.get_related_questions(
        db, source.id, limit=5, exclude_statuses=["REJECTED"]
    )

    assert other.id in [q.id for q in result]


def test_get_related_questions_ranks_by_weighted_score(db):
    close_vector = [0.1] * 1536
    far_vector = [0.9] * 1536

    source = _create_question_with_embedding(db, "元質問", "元回答", close_vector)
    similar = _create_question_with_embedding(
        db, "似ている質問", "似ている回答", close_vector
    )
    dissimilar = _create_question_with_embedding(
        db, "似ていない質問", "似ていない回答", far_vector
    )

    result = recommendation_service.get_related_questions(db, source.id, limit=5)

    result_ids = [q.id for q in result]
    assert similar.id in result_ids
    assert result_ids.index(similar.id) < result_ids.index(dissimilar.id)


def test_get_related_questions_includes_concept_sharing_candidate(db):
    vector = [0.1] * 1536
    other_vector = [-0.1] * 1536

    source = _create_question_with_embedding(db, "元質問", "元回答", vector)
    concept_sharing = _create_question_with_embedding(
        db, "概念を共有する質問", "共有回答", other_vector
    )

    concept = _create_concept(db, "共有概念", vector)
    question_concept_repository.link(db, question_id=source.id, concept_id=concept.id)
    question_concept_repository.link(
        db, question_id=concept_sharing.id, concept_id=concept.id
    )

    result = recommendation_service.get_related_questions(db, source.id, limit=5)

    assert concept_sharing.id in [q.id for q in result]


def test_get_related_questions_returns_empty_when_no_embedding(db):
    q = question_repository.create_question(db, question="埋め込みなし", answer="回答")
    db.flush()

    result = recommendation_service.get_related_questions(db, q.id, limit=5)

    assert result == []
