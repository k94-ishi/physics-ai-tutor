import pytest

from physics_ai_tutor.core.exceptions import ConceptExtractionError
from physics_ai_tutor.repositories import concept_repository, question_repository
from physics_ai_tutor.services import (
    concept_service,
    deepseek_service,
    embedding_service,
)
from physics_ai_tutor.services.concept_service import (
    extract_concept_names as real_extract_concept_names,
)


def _create_question(db, question="質問", answer="回答"):
    q = question_repository.create_question(db, question=question, answer=answer)
    db.flush()
    return q


def test_extract_concept_names_parses_newline_separated_list(monkeypatch):
    monkeypatch.setattr(
        deepseek_service,
        "chat_completion",
        lambda system_prompt, user_prompt: "加速度\n速度",
    )

    result = real_extract_concept_names(
        "加速度って何？", "単位時間あたりの速度の変化量です"
    )

    assert result == ["加速度", "速度"]


def test_extract_concept_names_strips_whitespace_and_blank_lines(monkeypatch):
    monkeypatch.setattr(
        deepseek_service,
        "chat_completion",
        lambda system_prompt, user_prompt: "  加速度  \n\n\n 速度 \n",
    )

    result = real_extract_concept_names("質問", "回答")

    assert result == ["加速度", "速度"]


def test_extract_concept_names_rejects_empty_output(monkeypatch):
    monkeypatch.setattr(
        deepseek_service,
        "chat_completion",
        lambda system_prompt, user_prompt: "\n\n   \n",
    )

    with pytest.raises(ConceptExtractionError):
        real_extract_concept_names("質問", "回答")


def test_attach_concepts_to_question_creates_new_concepts(db):
    question = _create_question(db)

    concept_service.attach_concepts_to_question(
        db, question_id=question.id, concept_names=["加速度", "速度"]
    )

    concepts = concept_repository.list_all(db)

    assert {c.name for c in concepts} == {"加速度", "速度"}
    for c in concepts:
        assert c.embedding is not None
        assert (
            c.extraction_prompt_version
            == concept_service.CONCEPT_EXTRACTION_PROMPT_VERSION
        )


def test_attach_concepts_to_question_embeds_the_name_only(db, monkeypatch):
    question = _create_question(db)
    captured = []

    def fake_create_embeddings(texts):
        captured.extend(texts)
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(embedding_service, "create_embeddings", fake_create_embeddings)

    concept_service.attach_concepts_to_question(
        db, question_id=question.id, concept_names=["加速度"]
    )

    assert captured == ["加速度"]


def test_attach_concepts_to_question_reuses_existing_concept_by_name(db):
    question1 = _create_question(db, "質問1", "回答1")
    question2 = _create_question(db, "質問2", "回答2")

    concept_service.attach_concepts_to_question(
        db, question_id=question1.id, concept_names=["加速度"]
    )
    concept_service.attach_concepts_to_question(
        db, question_id=question2.id, concept_names=["加速度"]
    )

    concepts = concept_repository.list_all(db)

    assert len(concepts) == 1


def test_attach_concepts_to_question_dedupes_within_same_call(db):
    question = _create_question(db)

    concepts = concept_service.attach_concepts_to_question(
        db, question_id=question.id, concept_names=["加速度", "加速度"]
    )

    assert len(concepts) == 1
    assert len(concept_repository.list_all(db)) == 1
