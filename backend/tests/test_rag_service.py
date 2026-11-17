import pytest

from physics_ai_tutor.core import prompts
from physics_ai_tutor.services import rag_service
from tests.conftest import (
    create_concept,
    create_embedding,
    create_question,
    fake_generation,
    link_concept,
    patch_create_embeddings,
    patch_generation,
)

DIM = 1536


def _vector(index: int, value: float = 1.0) -> list[float]:
    v = [0.0] * DIM
    v[index] = value
    return v


def _create_question(db, question="質問", answer="回答", status="APPROVED"):
    return create_question(db, question=question, answer=answer, status=status)


def _embed_question(db, question, vector):
    create_embedding(
        db,
        question_id=question.id,
        embedding=vector,
        embedding_type="question",
        model="text-embedding-3-small",
    )


def _stub_query_embedding(monkeypatch, vector):
    patch_create_embeddings(monkeypatch, lambda texts: [vector])


@pytest.mark.anyio
async def test_retrieve_context_filters_by_min_score(async_db, db, monkeypatch):
    near = _create_question(db, "近い質問", "近い回答")
    far = _create_question(db, "遠い質問", "遠い回答")

    _embed_question(db, near, _vector(0))
    _embed_question(db, far, _vector(1))

    _stub_query_embedding(monkeypatch, _vector(0))

    db.commit()

    context = await rag_service.retrieve_context(async_db, "クエリ")

    assert [c.id for c in context] == [near.id]
    assert context[0].score == pytest.approx(1.0, abs=1e-3)


@pytest.mark.anyio
async def test_retrieve_context_excludes_unreviewed_and_rejected(
    async_db, db, monkeypatch
):
    approved = _create_question(db, "承認済み質問", "回答", status="APPROVED")
    unreviewed = _create_question(db, "未レビュー質問", "回答", status="UNREVIEWED")
    rejected = _create_question(db, "却下質問", "回答", status="REJECTED")

    for question in (approved, unreviewed, rejected):
        _embed_question(db, question, _vector(0))

    _stub_query_embedding(monkeypatch, _vector(0))

    db.commit()

    context = await rag_service.retrieve_context(async_db, "クエリ")

    assert [c.id for c in context] == [approved.id]


@pytest.mark.anyio
async def test_retrieve_context_includes_concepts(async_db, db, monkeypatch):
    question = _create_question(db, "質問", "回答")
    _embed_question(db, question, _vector(0))

    concept = create_concept(
        db,
        name="力学",
        embedding=_vector(2),
        extraction_model="test-model",
        embedding_model="test-model",
        extraction_prompt_version="v1",
    )
    link_concept(db, question_id=question.id, concept_id=concept.id)

    _stub_query_embedding(monkeypatch, _vector(0))

    db.commit()

    context = await rag_service.retrieve_context(async_db, "クエリ")

    assert context[0].concepts == ["力学"]


@pytest.mark.anyio
async def test_retrieve_context_respects_top_k_limit(async_db, db, monkeypatch):
    questions = [_create_question(db, f"質問{i}", f"回答{i}") for i in range(6)]
    for question in questions:
        _embed_question(db, question, _vector(0))

    _stub_query_embedding(monkeypatch, _vector(0))

    db.commit()

    context = await rag_service.retrieve_context(async_db, "クエリ")

    assert len(context) == rag_service.RAG_TOP_K


def test_build_context_prompt_includes_question_answer_concepts():
    context = [
        rag_service.RetrievedQuestion(
            id=1, question="Q1", answer="A1", concepts=["力学"], score=0.9
        ),
    ]

    prompt = rag_service.build_context_prompt("新しい質問", context)

    assert "Q1" in prompt
    assert "A1" in prompt
    assert "力学" in prompt
    assert "新しい質問" in prompt


def test_build_context_prompt_without_context_returns_question_only():
    prompt = rag_service.build_context_prompt("質問だけ", [])

    assert prompt == "質問だけ"


@pytest.mark.anyio
async def test_generate_rag_answer_uses_rag_system_prompt_and_returns_ids(
    async_db, db, monkeypatch
):
    question = _create_question(
        db, "力とは何ですか", "力は物体を変形・加速させる作用です"
    )
    _embed_question(db, question, _vector(0))
    _stub_query_embedding(monkeypatch, _vector(0))

    calls = []

    def fake_generate_answer(system_prompt, user_prompt):
        calls.append((system_prompt, user_prompt))
        return fake_generation("生成された回答")(system_prompt, user_prompt)

    patch_generation(monkeypatch, fake_generate_answer)

    db.commit()

    result, ids = await rag_service.generate_rag_answer(async_db, "力の説明をして")

    assert result.content == "生成された回答"
    assert result.model == "mock-model"
    assert ids == [question.id]
    assert calls[0][0] == prompts.RAG_SYSTEM_PROMPT
    assert "力とは何ですか" in calls[0][1]


@pytest.mark.anyio
async def test_generate_rag_answer_without_context_still_answers(
    async_db, db, monkeypatch
):
    _stub_query_embedding(monkeypatch, _vector(0))
    patch_generation(monkeypatch, fake_generation("回答"))

    db.commit()

    result, ids = await rag_service.generate_rag_answer(
        async_db, "誰も答えたことのない質問"
    )

    assert result.content == "回答"
    assert ids == []


@pytest.mark.anyio
async def test_load_context_by_ids_preserves_order(async_db, db):
    first = _create_question(db, "質問1", "回答1")
    second = _create_question(db, "質問2", "回答2")

    db.commit()

    context = await rag_service.load_context_by_ids(async_db, [second.id, first.id])

    assert [c.id for c in context] == [second.id, first.id]


@pytest.mark.anyio
async def test_load_context_by_ids_excludes_unapproved(async_db, db):
    approved = _create_question(db, "承認済み質問", "回答", status="APPROVED")
    unreviewed = _create_question(db, "未レビュー質問", "回答", status="UNREVIEWED")

    db.commit()

    context = await rag_service.load_context_by_ids(
        async_db, [approved.id, unreviewed.id]
    )

    assert [c.id for c in context] == [approved.id]


@pytest.mark.anyio
async def test_load_context_by_ids_caps_at_top_k(async_db, db):
    questions = [_create_question(db, f"質問{i}", f"回答{i}") for i in range(6)]

    db.commit()

    context = await rag_service.load_context_by_ids(async_db, [q.id for q in questions])

    assert len(context) == rag_service.RAG_TOP_K


@pytest.mark.anyio
async def test_load_context_by_ids_includes_concepts(async_db, db):
    question = _create_question(db, "質問", "回答")
    concept = create_concept(
        db,
        name="力学",
        embedding=_vector(2),
        extraction_model="test-model",
        embedding_model="test-model",
        extraction_prompt_version="v1",
    )
    link_concept(db, question_id=question.id, concept_id=concept.id)

    db.commit()

    context = await rag_service.load_context_by_ids(async_db, [question.id])

    assert context[0].concepts == ["力学"]


@pytest.mark.anyio
async def test_load_context_by_ids_empty_list_returns_empty(async_db, db):
    db.commit()

    assert await rag_service.load_context_by_ids(async_db, []) == []


@pytest.mark.anyio
async def test_generate_rag_answer_with_ids_skips_embedding_search(
    async_db, db, monkeypatch
):
    question = _create_question(
        db, "力とは何ですか", "力は物体を変形・加速させる作用です"
    )

    def _fail_create_embeddings(texts):
        raise AssertionError("create_embeddings should not be called")

    patch_create_embeddings(monkeypatch, _fail_create_embeddings)
    patch_generation(monkeypatch, fake_generation("回答"))

    db.commit()

    result, ids = await rag_service.generate_rag_answer(
        async_db, "力の説明をして", retrieved_question_ids=[question.id]
    )

    assert result.content == "回答"
    assert ids == [question.id]


@pytest.mark.anyio
async def test_generate_rag_answer_falls_back_to_search_when_no_approved_ids(
    async_db, db, monkeypatch
):
    question = _create_question(db, "力とは何ですか", "力は説明です")
    _embed_question(db, question, _vector(0))
    _stub_query_embedding(monkeypatch, _vector(0))
    patch_generation(monkeypatch, fake_generation("回答"))

    db.commit()

    result, ids = await rag_service.generate_rag_answer(
        async_db, "力の説明をして", retrieved_question_ids=None
    )

    assert result.content == "回答"
    assert ids == [question.id]
