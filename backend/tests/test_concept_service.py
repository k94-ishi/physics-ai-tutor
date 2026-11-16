import asyncio

import pytest

from physics_ai_tutor.core.exceptions import ConceptExtractionError
from physics_ai_tutor.models import Concept
from physics_ai_tutor.services import (
    concept_service,
)
from tests.conftest import (
    attach_concepts,
    create_question,
    patch_chat_completion,
    patch_create_embeddings,
)

# Captured before conftest's autouse mock replaces the seam ([95]).
_real_async_extract = concept_service.async_extract_concept_names


def real_extract_concept_names(*args, **kwargs):
    return asyncio.run(_real_async_extract(*args, **kwargs))


def _create_question(db, question="質問", answer="回答"):
    q = create_question(db, question=question, answer=answer)
    # Committed: concepts are attached through the async service's session.
    db.commit()
    return q


def test_extract_concept_names_parses_newline_separated_list(monkeypatch):
    patch_chat_completion(
        monkeypatch, lambda system_prompt, user_prompt: "加速度\n速度"
    )

    result = real_extract_concept_names(
        "加速度って何？", "単位時間あたりの速度の変化量です"
    )

    assert result == ["加速度", "速度"]


def test_extract_concept_names_strips_whitespace_and_blank_lines(monkeypatch):
    patch_chat_completion(
        monkeypatch, lambda system_prompt, user_prompt: "  加速度  \n\n\n 速度 \n"
    )

    result = real_extract_concept_names("質問", "回答")

    assert result == ["加速度", "速度"]


def test_extract_concept_names_rejects_empty_output(monkeypatch):
    patch_chat_completion(monkeypatch, lambda system_prompt, user_prompt: "\n\n   \n")

    with pytest.raises(ConceptExtractionError):
        real_extract_concept_names("質問", "回答")


def test_attach_concepts_to_question_creates_new_concepts(db):
    question = _create_question(db)

    attach_concepts(db, question.id, ["加速度", "速度"])

    concepts = db.query(Concept).all()

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

    patch_create_embeddings(monkeypatch, fake_create_embeddings)

    attach_concepts(db, question.id, ["加速度"])

    assert captured == ["加速度"]


def test_attach_concepts_to_question_reuses_existing_concept_by_name(db):
    question1 = _create_question(db, "質問1", "回答1")
    question2 = _create_question(db, "質問2", "回答2")

    attach_concepts(db, question1.id, ["加速度"])
    attach_concepts(db, question2.id, ["加速度"])

    concepts = db.query(Concept).all()

    assert len(concepts) == 1


def test_attach_concepts_to_question_dedupes_within_same_call(db):
    question = _create_question(db)

    concepts = attach_concepts(db, question.id, ["加速度", "加速度"])

    assert len(concepts) == 1
    assert len(db.query(Concept).all()) == 1


LEVELS_LINE = "LEVELS: physics=1 math=1"


def test_parse_levels_line_reads_the_required_format():
    levels = concept_service.parse_levels_line(LEVELS_LINE)

    assert levels == concept_service.ExtractionLevels(1, 1)
    # Tolerant of case and spacing; the model is not a formatter.
    assert concept_service.parse_levels_line(
        "levels: physics = 3 math = 2"
    ) == concept_service.ExtractionLevels(3, 2)


def test_parse_levels_line_clamps_and_rejects_garbage():
    # The scale is ordinal; an overshoot means "at least the top".
    clamped = concept_service.parse_levels_line("LEVELS: physics=9 math=5")
    assert clamped == concept_service.ExtractionLevels(4, 4)

    for junk in (
        "LEVELS: question physics=1 math=0 | answer physics=1 math=1",
        "question physics=1 math=0 | answer physics=1 math=1",
        "LEVELS: physics=a math=0",
        "概念A | concept A",
        "",
    ):
        assert concept_service.parse_levels_line(junk) is None, junk


def test_levels_line_is_metadata_not_a_concept(db):
    question = _create_question(db)

    attach_concepts(db, question.id, ["加速度 | acceleration", LEVELS_LINE])

    names = {c.name for c in db.query(Concept).all()}
    assert names == {"加速度"}, "the levels line must never become a concept"


def test_apply_levels_to_question_stores_and_tolerates_absence(db):
    question = _create_question(db)

    concept_service.apply_levels_to_question(question, ["概念A | concept A"])
    assert question.physics_level is None, "no line, no change"

    concept_service.apply_levels_to_question(
        question, ["概念A | concept A", LEVELS_LINE]
    )
    assert question.physics_level == 1
    assert question.math_level == 1
