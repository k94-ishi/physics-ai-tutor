import pytest
from sqlalchemy.exc import IntegrityError

from physics_ai_tutor.models import Concept, Question, QuestionConcept, QuestionReview
from physics_ai_tutor.services.user_service import create_user


def _create_question(db, question="質問", answer="回答"):
    q = Question(question=question, answer=answer)
    db.add(q)
    db.flush()
    return q


def _create_concept(db, name="概念"):
    c = Concept(
        name=name,
        embedding=[0.1] * 1536,
        extraction_model="test-model",
        embedding_model="test-model",
        extraction_prompt_version="v1",
    )
    db.add(c)
    db.flush()
    return c


def test_question_defaults_status_and_source(db):
    q = _create_question(db)
    db.commit()
    db.refresh(q)

    assert q.status == "APPROVED"
    assert q.source == "MANUAL"


def test_concept_name_must_be_unique(db):
    _create_concept(db, "重複概念")

    with pytest.raises(IntegrityError):
        _create_concept(db, "重複概念")


def test_question_concept_cascades_on_question_delete(db):
    question = _create_question(db)
    concept = _create_concept(db)
    db.add(QuestionConcept(question_id=question.id, concept_id=concept.id))
    db.commit()

    db.delete(question)
    db.commit()

    remaining = (
        db.query(QuestionConcept).filter(QuestionConcept.concept_id == concept.id).all()
    )
    assert remaining == []


def test_question_concept_cascades_on_concept_delete(db):
    question = _create_question(db)
    concept = _create_concept(db)
    db.add(QuestionConcept(question_id=question.id, concept_id=concept.id))
    db.commit()

    db.delete(concept)
    db.commit()

    remaining = (
        db.query(QuestionConcept)
        .filter(QuestionConcept.question_id == question.id)
        .all()
    )
    assert remaining == []


def test_question_review_cascades_on_question_delete(db):
    question = _create_question(db)
    admin = create_user(
        db, "model-reviewer@example.com", "reviewerpass123", role="admin"
    )

    db.add(
        QuestionReview(
            question_id=question.id,
            action="APPROVE",
            reviewer_id=admin.id,
            before_question=question.question,
            before_answer=question.answer,
            after_question=question.question,
            after_answer=question.answer,
        )
    )
    db.commit()

    db.delete(question)
    db.commit()

    remaining = (
        db.query(QuestionReview).filter(QuestionReview.question_id == question.id).all()
    )
    assert remaining == []
