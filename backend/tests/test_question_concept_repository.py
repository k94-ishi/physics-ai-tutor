import pytest

from physics_ai_tutor.repositories import (
    question_concept_repository,
)
from tests.conftest import create_concept, create_question, link_concept


def _create_question(db, question="質問", answer="回答"):
    q = create_question(db, question=question, answer=answer)
    db.flush()
    return q


def _create_concept(db, name="概念"):
    c = create_concept(
        db,
        name=name,
        embedding=[0.1] * 1536,
        extraction_model="test-model",
        embedding_model="test-model",
        extraction_prompt_version="v1",
    )
    db.flush()
    return c


# Production links through `link_many` ([91]); these test it directly.


@pytest.mark.anyio
async def test_link_creates_relation(db, async_db):
    question = _create_question(db)
    concept = _create_concept(db)
    db.commit()

    await question_concept_repository.link_many(async_db, question.id, [concept.id])

    concepts = await question_concept_repository.get_concepts_for_question(
        async_db, question.id
    )
    assert [c.id for c in concepts] == [concept.id]


@pytest.mark.anyio
async def test_link_is_idempotent(db, async_db):
    question = _create_question(db)
    concept = _create_concept(db)
    db.commit()

    # A repeated id in one call, and the same link again in a second call.
    link_many = question_concept_repository.link_many
    await link_many(async_db, question.id, [concept.id, concept.id])
    await link_many(async_db, question.id, [concept.id])

    concepts = await question_concept_repository.get_concepts_for_question(
        async_db, question.id
    )
    assert len(concepts) == 1


@pytest.mark.anyio
async def test_get_concepts_for_question_empty(db, async_db):
    question = _create_question(db)
    db.commit()

    concepts = await question_concept_repository.get_concepts_for_question(
        async_db, question.id
    )
    assert concepts == []


@pytest.mark.anyio
async def test_get_concepts_for_questions_groups_by_question(db, async_db):
    q1 = _create_question(db, "質問1", "回答1")
    q2 = _create_question(db, "質問2", "回答2")
    q3 = _create_question(db, "質問3", "回答3")

    c1 = _create_concept(db, "概念A")
    c2 = _create_concept(db, "概念B")

    link_concept(db, question_id=q1.id, concept_id=c1.id)
    link_concept(db, question_id=q1.id, concept_id=c2.id)
    link_concept(db, question_id=q2.id, concept_id=c1.id)

    db.commit()

    result = await question_concept_repository.get_concepts_for_questions(
        async_db, [q1.id, q2.id, q3.id]
    )

    assert set(result[q1.id]) == {"概念A", "概念B"}
    assert result[q2.id] == ["概念A"]
    assert result[q3.id] == []


@pytest.mark.anyio
async def test_get_concepts_for_questions_empty_ids_returns_empty_dict(async_db):
    result = await question_concept_repository.get_concepts_for_questions(async_db, [])

    assert result == {}


@pytest.mark.anyio
async def test_get_questions_sharing_concepts(db, async_db):
    q1 = _create_question(db, "質問1", "回答1")
    q2 = _create_question(db, "質問2", "回答2")
    q3 = _create_question(db, "質問3", "回答3")

    shared_concept = _create_concept(db, "共有概念")
    other_concept = _create_concept(db, "他の概念")

    link_concept(db, question_id=q1.id, concept_id=shared_concept.id)
    link_concept(db, question_id=q2.id, concept_id=shared_concept.id)
    link_concept(db, question_id=q3.id, concept_id=other_concept.id)
    db.commit()

    result = await question_concept_repository.get_questions_sharing_concepts(
        async_db, question_id=q1.id, exclude_ids=[], limit=10
    )

    assert result == [q2.id]


@pytest.mark.anyio
async def test_get_questions_sharing_concepts_respects_exclude_ids(db, async_db):
    q1 = _create_question(db, "質問1", "回答1")
    q2 = _create_question(db, "質問2", "回答2")

    concept = _create_concept(db)
    link_concept(db, question_id=q1.id, concept_id=concept.id)
    link_concept(db, question_id=q2.id, concept_id=concept.id)
    db.commit()

    result = await question_concept_repository.get_questions_sharing_concepts(
        async_db, question_id=q1.id, exclude_ids=[q2.id], limit=10
    )

    assert result == []


@pytest.mark.anyio
async def test_approved_links_sharing_concepts_skips_self_and_unapproved(db, async_db):
    current = _create_question(db, "現在の質問", "回答")
    approved = _create_question(db, "承認済み", "回答")
    hidden = _create_question(db, "未レビュー", "回答")
    hidden.status = "UNREVIEWED"
    db.flush()
    concept = _create_concept(db, "共有概念")
    for question in (current, approved, hidden):
        link_concept(db, question_id=question.id, concept_id=concept.id)
    db.commit()

    links = await question_concept_repository.approved_links_sharing_concepts(
        async_db, current.id
    )

    assert [(c.id, q.id) for c, q in links] == [(concept.id, approved.id)]


@pytest.mark.anyio
async def test_concept_readers_return_the_linked_concept(db, async_db):
    question = _create_question(db)
    concept = _create_concept(db, "概念A")
    link_concept(db, question_id=question.id, concept_id=concept.id)
    db.commit()

    concepts = await question_concept_repository.get_concepts_for_question(
        async_db, question.id
    )
    ids = await question_concept_repository.get_concept_ids_for_question(
        async_db, question.id
    )

    assert [c.id for c in concepts] == [concept.id]
    assert ids == [concept.id]


@pytest.mark.anyio
async def test_delete_by_question_id_removes_all_links(db, async_db):
    question = _create_question(db)
    c1 = _create_concept(db, "概念A")
    c2 = _create_concept(db, "概念B")

    link_concept(db, question_id=question.id, concept_id=c1.id)
    link_concept(db, question_id=question.id, concept_id=c2.id)
    db.commit()

    await question_concept_repository.delete_by_question_id(async_db, question.id)

    concepts = await question_concept_repository.get_concepts_for_question(
        async_db, question.id
    )
    assert concepts == []
