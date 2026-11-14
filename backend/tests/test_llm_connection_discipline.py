"""No transaction is open while an LLM call waits ([82]).

`test_architecture.py` has the lexical tripwire; these are the runtime
guarantees. Each test patches an LLM seam with a stub that records
whether the session was inside a transaction at the moment of the call -
in SQLAlchemy that is exactly when a pooled connection is checked out
and idle.
"""

import pytest
from sqlalchemy import select

from physics_ai_tutor.models import Question
from physics_ai_tutor.schemas.ai import AskAiRequest
from physics_ai_tutor.schemas.language import Language, TextProvenance
from physics_ai_tutor.schemas.question import QuestionSource, QuestionStatus
from physics_ai_tutor.services import (
    ai_review_service,
    ai_service,
    concept_service,
    deepseek_service,
    embedding_service,
    question_review_service,
    question_translation_service,
    question_write_service,
    translation_service,
)

pytestmark = pytest.mark.anyio


def _question(**overrides) -> Question:
    values = dict(
        question_ja="接続規律のテスト質問",
        answer_ja="テスト回答",
        ja_provenance=TextProvenance.ORIGINAL,
        original_language="ja",
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )
    values.update(overrides)
    return Question(**values)


async def test_translation_holds_no_transaction_during_the_llm_calls(
    async_db, monkeypatch
):
    in_transaction = {}

    async def _translate(question, answer, source, target):
        in_transaction["translate"] = async_db.in_transaction()
        return f"[{target}] {question}", f"[{target}] {answer}"

    async def _embed(texts):
        in_transaction["embed"] = async_db.in_transaction()
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(translation_service, "async_translate_qa", _translate)
    monkeypatch.setattr(embedding_service, "async_create_embeddings", _embed)

    async_db.add(_question(status=QuestionStatus.APPROVED))
    await async_db.commit()
    question_id = (await async_db.scalars(select(Question.id))).first()

    filled = await question_translation_service.async_translate_missing_languages(
        async_db, question_id
    )

    assert filled == [Language.EN]
    assert in_transaction == {"translate": False, "embed": False}

    # The write still happened, text and embeddings together.
    row = await async_db.get(Question, question_id)
    await async_db.refresh(row)
    assert row.question_en == "[en] 接続規律のテスト質問"


async def test_a_failed_translation_commits_nothing(async_db, monkeypatch):
    from physics_ai_tutor.core.exceptions import TranslationError

    async def _fail(question, answer, source, target):
        raise TranslationError("down")

    monkeypatch.setattr(translation_service, "async_translate_qa", _fail)

    async_db.add(_question(status=QuestionStatus.APPROVED))
    await async_db.commit()
    question_id = (await async_db.scalars(select(Question.id))).first()

    filled = await question_translation_service.async_translate_missing_languages(
        async_db, question_id
    )

    assert filled == []
    row = await async_db.get(Question, question_id)
    await async_db.refresh(row)
    assert row.question_en is None


async def test_the_direct_ask_holds_no_transaction_during_generation(
    async_db, monkeypatch
):
    seen = {}

    async def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        seen["in_transaction"] = async_db.in_transaction()
        return deepseek_service.GenerationResult("回答", "mock-model", 1, 2)

    monkeypatch.setattr(deepseek_service, "async_generate_answer", _generate)

    async def _record() -> None:
        pass

    outcome = await ai_service.ask(
        async_db,
        AskAiRequest(question="生成中の接続を調べる質問"),
        user_id=None,
        record_generation=_record,
        rate_limit_bucket="ip:test",
    )

    assert outcome.response.answer == "回答"
    assert seen["in_transaction"] is False


async def test_the_rag_ask_holds_no_transaction_during_generation(
    async_db, monkeypatch
):
    """The RAG path reads context first; those reads must not linger.

    This is the case [70] left broken: retrieval opened an implicit
    transaction that then sat through the whole generation.
    """
    seen = {}

    async def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        seen["in_transaction"] = async_db.in_transaction()
        return deepseek_service.GenerationResult("RAG回答", "mock-model", 1, 2)

    monkeypatch.setattr(deepseek_service, "async_generate_answer", _generate)

    async def _record() -> None:
        pass

    outcome = await ai_service.ask(
        async_db,
        AskAiRequest(question="RAG生成中の接続を調べる質問", mode="RAG"),
        user_id=None,
        record_generation=_record,
        rate_limit_bucket="ip:test",
    )

    assert outcome.response.answer == "RAG回答"
    assert seen["in_transaction"] is False


async def test_the_query_embedding_miss_holds_no_transaction(async_db, monkeypatch):
    seen = {}

    async def _embed(texts):
        seen["in_transaction"] = async_db.in_transaction()
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(embedding_service, "async_create_embeddings", _embed)

    await embedding_service.async_embed_query(async_db, "初めて来る検索クエリ")

    assert seen["in_transaction"] is False


async def test_the_ai_review_holds_no_transaction_during_grading(async_db, monkeypatch):
    seen = {}

    async def _grade(system_prompt, user_prompt, temperature=None, **kwargs):
        seen["in_transaction"] = async_db.in_transaction()
        return deepseek_service.GenerationResult(
            '{"verdict": "APPROVE", "confidence": 0.9, "reasons": [],'
            ' "rationale": "ok", "suggested_answer": null, "rubric": {}}',
            "mock-model",
            1,
            2,
        )

    monkeypatch.setattr(deepseek_service, "async_generate_answer", _grade)

    question = _question()
    async_db.add(question)
    await async_db.commit()

    row = await ai_review_service.async_review_question(async_db, question)

    assert row is not None
    assert seen["in_transaction"] is False


async def test_concept_reextraction_holds_no_transaction_during_llm_calls(
    async_db, monkeypatch
):
    """Extraction and the new-sense embedding both run with no transaction ([91])."""
    in_transaction = {}

    async def _extract(question, answer, language="ja"):
        in_transaction["extract"] = async_db.in_transaction()
        return ["新しい概念 | new concept"]

    async def _embed(texts):
        in_transaction["embed"] = async_db.in_transaction()
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(concept_service, "async_extract_concept_names", _extract)
    monkeypatch.setattr(embedding_service, "async_create_embeddings", _embed)

    async_db.add(_question(status=QuestionStatus.APPROVED))
    await async_db.commit()
    question_id = (await async_db.scalars(select(Question.id))).first()

    results = await question_write_service.reextract_concepts_for_questions(
        async_db, [question_id]
    )

    assert results[0].success is True
    assert results[0].concepts == ["新しい概念"]
    assert in_transaction == {"extract": False, "embed": False}


async def test_edit_approve_holds_no_transaction_during_llm_calls(
    async_db, monkeypatch
):
    """Embedding, translation and extraction all wait with no transaction ([85])."""
    from physics_ai_tutor.models import User
    from physics_ai_tutor.schemas.question_review import QuestionReviewAction

    seen = []

    async def _embed(texts):
        seen.append(("embed", async_db.in_transaction()))
        return [[0.1] * 1536 for _ in texts]

    async def _translate(question, answer, source, target):
        seen.append(("translate", async_db.in_transaction()))
        return f"[{target}] {question}", f"[{target}] {answer}"

    async def _extract(question, answer, language="ja"):
        seen.append(("extract", async_db.in_transaction()))
        return ["概念A | concept A"]

    monkeypatch.setattr(embedding_service, "async_create_embeddings", _embed)
    monkeypatch.setattr(translation_service, "async_translate_qa", _translate)
    monkeypatch.setattr(concept_service, "async_extract_concept_names", _extract)

    async_db.add(_question())
    async_db.add(User(email="probe@example.com", hashed_password="x", role="admin"))
    await async_db.commit()
    question_id = (await async_db.scalars(select(Question.id))).first()
    reviewer_id = (await async_db.scalars(select(User.id))).first()

    reviewed = await question_review_service.review_question(
        async_db,
        question_id,
        action=QuestionReviewAction.EDIT_APPROVE,
        reviewer_id=reviewer_id,
        question="編集後の質問",
        answer="編集後の回答",
        reason="PHYSICS_ERROR",
    )

    assert reviewed is not None and reviewed.status == QuestionStatus.APPROVED
    assert {kind for kind, _ in seen} == {"embed", "translate", "extract"}
    assert all(open_ is False for _, open_ in seen), seen


async def test_create_holds_no_transaction_during_llm_calls(async_db, monkeypatch):
    """Embedding, extraction and translation of a new row wait unheld ([93])."""
    from physics_ai_tutor.schemas.question import QuestionCreate

    seen = []

    async def _embed(texts):
        seen.append(("embed", async_db.in_transaction()))
        return [[0.1] * 1536 for _ in texts]

    async def _translate(question, answer, source, target):
        seen.append(("translate", async_db.in_transaction()))
        return f"[{target}] {question}", f"[{target}] {answer}"

    async def _extract(question, answer, language="ja"):
        seen.append(("extract", async_db.in_transaction()))
        return ["概念A | concept A"]

    monkeypatch.setattr(embedding_service, "async_create_embeddings", _embed)
    monkeypatch.setattr(translation_service, "async_translate_qa", _translate)
    monkeypatch.setattr(concept_service, "async_extract_concept_names", _extract)

    created = await question_write_service.create_question(
        async_db, QuestionCreate(question="新しい質問", answer="新しい回答")
    )

    assert created.question_en == "[en] 新しい質問"
    assert {kind for kind, _ in seen} == {"embed", "translate", "extract"}
    assert all(open_ is False for _, open_ in seen), seen


async def test_import_holds_no_transaction_during_llm_calls(async_db, monkeypatch):
    """Embedding, extraction and translation of imported rows wait unheld ([94])."""
    from physics_ai_tutor.schemas.question import QuestionCreate

    seen = []

    async def _embed(texts):
        seen.append(("embed", async_db.in_transaction()))
        return [[0.1] * 1536 for _ in texts]

    async def _translate(question, answer, source, target):
        seen.append(("translate", async_db.in_transaction()))
        return f"[{target}] {question}", f"[{target}] {answer}"

    async def _extract(question, answer, language="ja"):
        seen.append(("extract", async_db.in_transaction()))
        return ["概念A | concept A"]

    monkeypatch.setattr(embedding_service, "async_create_embeddings", _embed)
    monkeypatch.setattr(translation_service, "async_translate_qa", _translate)
    monkeypatch.setattr(concept_service, "async_extract_concept_names", _extract)

    created = await question_write_service.import_questions_from_jsonl(
        async_db,
        [QuestionCreate(question="取り込み質問", answer="取り込み回答")],
        status=QuestionStatus.APPROVED,
        source=QuestionSource.MANUAL,
    )

    assert created[0].question_en == "[en] 取り込み質問"
    assert {kind for kind, _ in seen} == {"embed", "translate", "extract"}
    assert all(open_ is False for _, open_ in seen), seen
