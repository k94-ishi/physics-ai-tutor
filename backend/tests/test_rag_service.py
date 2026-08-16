import pytest

from physics_ai_tutor.core import prompts
from physics_ai_tutor.repositories import (
    concept_repository,
    embedding_repository,
    question_concept_repository,
    question_repository,
)
from physics_ai_tutor.services import deepseek_service, embedding_service, rag_service

DIM = 1536


def _vector(index: int, value: float = 1.0) -> list[float]:
    v = [0.0] * DIM
    v[index] = value
    return v


def _create_question(db, question="質問", answer="回答", status="APPROVED"):
    return question_repository.create_question(
        db, question=question, answer=answer, status=status
    )


def _embed_question(db, question, vector):
    embedding_repository.create_embedding(
        db,
        question_id=question.id,
        embedding=vector,
        embedding_type="question",
        model="text-embedding-3-small",
    )


def _stub_query_embedding(monkeypatch, vector):
    monkeypatch.setattr(embedding_service, "create_embeddings", lambda texts: [vector])


def test_retrieve_context_filters_by_min_score(db, monkeypatch):
    near = _create_question(db, "近い質問", "近い回答")
    far = _create_question(db, "遠い質問", "遠い回答")

    _embed_question(db, near, _vector(0))
    _embed_question(db, far, _vector(1))

    _stub_query_embedding(monkeypatch, _vector(0))

    context = rag_service.retrieve_context(db, "クエリ")

    assert [c.id for c in context] == [near.id]
    assert context[0].score == pytest.approx(1.0, abs=1e-3)


def test_retrieve_context_excludes_unreviewed_and_rejected(db, monkeypatch):
    approved = _create_question(db, "承認済み質問", "回答", status="APPROVED")
    unreviewed = _create_question(db, "未レビュー質問", "回答", status="UNREVIEWED")
    rejected = _create_question(db, "却下質問", "回答", status="REJECTED")

    for question in (approved, unreviewed, rejected):
        _embed_question(db, question, _vector(0))

    _stub_query_embedding(monkeypatch, _vector(0))

    context = rag_service.retrieve_context(db, "クエリ")

    assert [c.id for c in context] == [approved.id]


def test_retrieve_context_includes_concepts(db, monkeypatch):
    question = _create_question(db, "質問", "回答")
    _embed_question(db, question, _vector(0))

    concept = concept_repository.create(
        db,
        name="力学",
        embedding=_vector(2),
        extraction_model="test-model",
        embedding_model="test-model",
        extraction_prompt_version="v1",
    )
    question_concept_repository.link(db, question_id=question.id, concept_id=concept.id)

    _stub_query_embedding(monkeypatch, _vector(0))

    context = rag_service.retrieve_context(db, "クエリ")

    assert context[0].concepts == ["力学"]


def test_retrieve_context_respects_top_k_limit(db, monkeypatch):
    questions = [_create_question(db, f"質問{i}", f"回答{i}") for i in range(6)]
    for question in questions:
        _embed_question(db, question, _vector(0))

    _stub_query_embedding(monkeypatch, _vector(0))

    context = rag_service.retrieve_context(db, "クエリ")

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


def test_generate_rag_answer_uses_rag_system_prompt_and_returns_ids(db, monkeypatch):
    question = _create_question(
        db, "力とは何ですか", "力は物体を変形・加速させる作用です"
    )
    _embed_question(db, question, _vector(0))
    _stub_query_embedding(monkeypatch, _vector(0))

    calls = []

    def fake_chat_completion(system_prompt, user_prompt):
        calls.append((system_prompt, user_prompt))
        return "生成された回答"

    monkeypatch.setattr(deepseek_service, "chat_completion", fake_chat_completion)

    answer, ids = rag_service.generate_rag_answer(db, "力の説明をして")

    assert answer == "生成された回答"
    assert ids == [question.id]
    assert calls[0][0] == prompts.RAG_SYSTEM_PROMPT
    assert "力とは何ですか" in calls[0][1]


def test_generate_rag_answer_without_context_still_answers(db, monkeypatch):
    _stub_query_embedding(monkeypatch, _vector(0))
    monkeypatch.setattr(
        deepseek_service, "chat_completion", lambda system_prompt, user_prompt: "回答"
    )

    answer, ids = rag_service.generate_rag_answer(db, "誰も答えたことのない質問")

    assert answer == "回答"
    assert ids == []


def test_load_context_by_ids_preserves_order(db):
    first = _create_question(db, "質問1", "回答1")
    second = _create_question(db, "質問2", "回答2")

    context = rag_service.load_context_by_ids(db, [second.id, first.id])

    assert [c.id for c in context] == [second.id, first.id]


def test_load_context_by_ids_excludes_unapproved(db):
    approved = _create_question(db, "承認済み質問", "回答", status="APPROVED")
    unreviewed = _create_question(db, "未レビュー質問", "回答", status="UNREVIEWED")

    context = rag_service.load_context_by_ids(db, [approved.id, unreviewed.id])

    assert [c.id for c in context] == [approved.id]


def test_load_context_by_ids_caps_at_top_k(db):
    questions = [_create_question(db, f"質問{i}", f"回答{i}") for i in range(6)]

    context = rag_service.load_context_by_ids(db, [q.id for q in questions])

    assert len(context) == rag_service.RAG_TOP_K


def test_load_context_by_ids_includes_concepts(db):
    question = _create_question(db, "質問", "回答")
    concept = concept_repository.create(
        db,
        name="力学",
        embedding=_vector(2),
        extraction_model="test-model",
        embedding_model="test-model",
        extraction_prompt_version="v1",
    )
    question_concept_repository.link(db, question_id=question.id, concept_id=concept.id)

    context = rag_service.load_context_by_ids(db, [question.id])

    assert context[0].concepts == ["力学"]


def test_load_context_by_ids_empty_list_returns_empty(db):
    assert rag_service.load_context_by_ids(db, []) == []


def test_generate_rag_answer_with_ids_skips_embedding_search(db, monkeypatch):
    question = _create_question(
        db, "力とは何ですか", "力は物体を変形・加速させる作用です"
    )

    def _fail_create_embeddings(texts):
        raise AssertionError("create_embeddings should not be called")

    monkeypatch.setattr(embedding_service, "create_embeddings", _fail_create_embeddings)
    monkeypatch.setattr(
        deepseek_service, "chat_completion", lambda system_prompt, user_prompt: "回答"
    )

    answer, ids = rag_service.generate_rag_answer(
        db, "力の説明をして", retrieved_question_ids=[question.id]
    )

    assert answer == "回答"
    assert ids == [question.id]


def test_generate_rag_answer_falls_back_to_search_when_no_approved_ids(db, monkeypatch):
    question = _create_question(db, "力とは何ですか", "力は説明です")
    _embed_question(db, question, _vector(0))
    _stub_query_embedding(monkeypatch, _vector(0))
    monkeypatch.setattr(
        deepseek_service, "chat_completion", lambda system_prompt, user_prompt: "回答"
    )

    answer, ids = rag_service.generate_rag_answer(
        db, "力の説明をして", retrieved_question_ids=None
    )

    assert answer == "回答"
    assert ids == [question.id]
