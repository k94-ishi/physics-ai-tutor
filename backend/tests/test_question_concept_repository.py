from physics_ai_tutor.repositories import (
    concept_repository,
    question_concept_repository,
    question_repository,
)


def _create_question(db, question="質問", answer="回答"):
    q = question_repository.create_question(db, question=question, answer=answer)
    db.flush()
    return q


def _create_concept(db, name="概念"):
    c = concept_repository.create(
        db,
        name=name,
        embedding=[0.1] * 1536,
        extraction_model="test-model",
        embedding_model="test-model",
        extraction_prompt_version="v1",
    )
    db.flush()
    return c


def test_link_creates_relation(db):
    question = _create_question(db)
    concept = _create_concept(db)

    question_concept_repository.link(db, question_id=question.id, concept_id=concept.id)

    concepts = question_concept_repository.get_concepts_for_question(db, question.id)
    assert [c.name for c in concepts] == [concept.name]


def test_link_is_idempotent(db):
    question = _create_question(db)
    concept = _create_concept(db)

    question_concept_repository.link(db, question_id=question.id, concept_id=concept.id)
    question_concept_repository.link(db, question_id=question.id, concept_id=concept.id)

    concepts = question_concept_repository.get_concepts_for_question(db, question.id)
    assert len(concepts) == 1


def test_get_concepts_for_question_empty(db):
    question = _create_question(db)

    assert question_concept_repository.get_concepts_for_question(db, question.id) == []


def test_get_concepts_for_questions_groups_by_question(db):
    q1 = _create_question(db, "質問1", "回答1")
    q2 = _create_question(db, "質問2", "回答2")
    q3 = _create_question(db, "質問3", "回答3")

    c1 = _create_concept(db, "概念A")
    c2 = _create_concept(db, "概念B")

    question_concept_repository.link(db, question_id=q1.id, concept_id=c1.id)
    question_concept_repository.link(db, question_id=q1.id, concept_id=c2.id)
    question_concept_repository.link(db, question_id=q2.id, concept_id=c1.id)

    result = question_concept_repository.get_concepts_for_questions(
        db, [q1.id, q2.id, q3.id]
    )

    assert set(result[q1.id]) == {"概念A", "概念B"}
    assert result[q2.id] == ["概念A"]
    assert result[q3.id] == []


def test_get_concepts_for_questions_empty_ids_returns_empty_dict(db):
    assert question_concept_repository.get_concepts_for_questions(db, []) == {}


def test_get_questions_sharing_concepts(db):
    q1 = _create_question(db, "質問1", "回答1")
    q2 = _create_question(db, "質問2", "回答2")
    q3 = _create_question(db, "質問3", "回答3")

    shared_concept = _create_concept(db, "共有概念")
    other_concept = _create_concept(db, "他の概念")

    question_concept_repository.link(
        db, question_id=q1.id, concept_id=shared_concept.id
    )
    question_concept_repository.link(
        db, question_id=q2.id, concept_id=shared_concept.id
    )
    question_concept_repository.link(
        db, question_id=q3.id, concept_id=other_concept.id
    )

    result = question_concept_repository.get_questions_sharing_concepts(
        db, question_id=q1.id, exclude_ids=[], limit=10
    )

    assert result == [q2.id]


def test_get_questions_sharing_concepts_respects_exclude_ids(db):
    q1 = _create_question(db, "質問1", "回答1")
    q2 = _create_question(db, "質問2", "回答2")

    concept = _create_concept(db)
    question_concept_repository.link(db, question_id=q1.id, concept_id=concept.id)
    question_concept_repository.link(db, question_id=q2.id, concept_id=concept.id)

    result = question_concept_repository.get_questions_sharing_concepts(
        db, question_id=q1.id, exclude_ids=[q2.id], limit=10
    )

    assert result == []


def test_delete_by_question_id_removes_all_links(db):
    question = _create_question(db)
    c1 = _create_concept(db, "概念A")
    c2 = _create_concept(db, "概念B")

    question_concept_repository.link(db, question_id=question.id, concept_id=c1.id)
    question_concept_repository.link(db, question_id=question.id, concept_id=c2.id)

    question_concept_repository.delete_by_question_id(db, question.id)

    assert question_concept_repository.get_concepts_for_question(db, question.id) == []
