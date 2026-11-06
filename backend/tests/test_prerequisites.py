"""Prerequisite block ([38]): ranking, exclusions, and the gap case."""

from physics_ai_tutor.models import Question
from physics_ai_tutor.repositories import (
    concept_repository,
    question_concept_repository,
)

QUESTIONS = "/api/v1/questions"


def _make_question(
    db,
    question_ja: str,
    status: str = "APPROVED",
    physics: int | None = None,
    math: int | None = None,
) -> Question:
    row = Question(
        question_ja=question_ja,
        answer_ja="回答",
        ja_provenance="ORIGINAL",
        original_language="ja",
        status=status,
        source="MANUAL",
        physics_level=physics,
        math_level=math,
    )
    db.add(row)
    db.commit()
    return row


def _link(db, question_id: int, name_ja: str, name_en: str) -> None:
    concept = concept_repository.get_by_name(db, name_ja, language="ja")
    if concept is None:
        concept = concept_repository.create(
            db,
            name_ja=name_ja,
            name_en=name_en,
            embedding=[0.1] * 1536,
            extraction_model="mock",
            embedding_model="mock",
            extraction_prompt_version="v6",
        )
    question_concept_repository.link(db, question_id=question_id, concept_id=concept.id)
    db.commit()


def test_lists_the_defining_qa_for_a_leaned_on_concept(client, db):
    """The air-resistance acceptance case: the ODE definer appears."""
    advanced = _make_question(db, "空気抵抗がある場合の放物運動は？", physics=2, math=3)
    definer = _make_question(db, "微分方程式ってなに？", physics=1, math=2)
    for question in (advanced, definer):
        _link(db, question.id, "微分方程式", "differential equation")

    body = client.get(f"{QUESTIONS}/{advanced.id}/prerequisites").json()

    assert [item["id"] for item in body["items"]] == [definer.id]
    assert "微分方程式" not in body["gaps"]


def test_never_lists_self_rejected_or_more_advanced_rows(client, db):
    current = _make_question(db, "単振り子ってなに？", physics=2, math=2)
    rejected = _make_question(
        db, "ベクトルってなに？", status="REJECTED", physics=1, math=1
    )
    too_advanced = _make_question(db, "ベクトルとはなにか？", physics=1, math=3)
    for question in (current, rejected, too_advanced):
        _link(db, question.id, "ベクトル", "vector")

    body = client.get(f"{QUESTIONS}/{current.id}/prerequisites").json()

    assert body["items"] == []
    # The concept is not silently dropped: it becomes a gap instead.
    assert "ベクトル" in body["gaps"]


def test_non_defining_neighbours_do_not_count_as_prerequisites(client, db):
    current = _make_question(db, "放物運動ってなに？", physics=1, math=2)
    neighbour = _make_question(
        db, "ボールを斜めに投げたらどうなる？", physics=1, math=1
    )
    for question in (current, neighbour):
        _link(db, question.id, "放物運動", "projectile motion")

    body = client.get(f"{QUESTIONS}/{current.id}/prerequisites").json()

    assert body["items"] == []
    assert body["gaps"] == ["放物運動"]


def test_one_card_per_qa_hardest_first_and_limit(client, db):
    current = _make_question(db, "減衰振動ってなに？", physics=3, math=3)
    easy = _make_question(db, "三角比ってなに？", physics=0, math=1)
    hard = _make_question(db, "微分方程式ってなに？", physics=1, math=3)
    _link(db, current.id, "三角比", "trigonometric ratio")
    _link(db, easy.id, "三角比", "trigonometric ratio")
    # `hard` defines two concepts of the current QA but appears once.
    for name_ja, name_en in (
        ("微分方程式", "differential equation"),
        ("微分", "differentiation"),
    ):
        _link(db, current.id, name_ja, name_en)
        _link(db, hard.id, name_ja, name_en)

    body = client.get(f"{QUESTIONS}/{current.id}/prerequisites").json()
    assert [item["id"] for item in body["items"]] == [hard.id, easy.id]

    limited = client.get(f"{QUESTIONS}/{current.id}/prerequisites?limit=1").json()
    assert [item["id"] for item in limited["items"]] == [hard.id]


def test_unrated_definers_pass_and_unknown_question_404s(client, db):
    current = _make_question(db, "波の干渉ってなに？", physics=3, math=1)
    unrated = _make_question(db, "波ってなに？")
    for question in (current, unrated):
        _link(db, question.id, "波", "wave")

    body = client.get(f"{QUESTIONS}/{current.id}/prerequisites").json()
    assert [item["id"] for item in body["items"]] == [unrated.id]

    assert client.get(f"{QUESTIONS}/999999/prerequisites").status_code == 404
