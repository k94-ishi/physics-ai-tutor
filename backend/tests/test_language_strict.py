"""Students never read the other language on the question page ([53])."""

import pytest

from physics_ai_tutor.models import BackgroundClaim, Question
from physics_ai_tutor.services import (
    background_translation_service,
    translation_service,
)
from tests.conftest import patch_translate_qa

QUESTIONS = "/api/v1/questions"


def _create(admin_client, question: str, translate: bool, monkeypatch) -> int:
    # The mocked extractor links every row to 概念A (has English) and 概念B (has not).
    with monkeypatch.context() as scoped:
        if not translate:

            def _fail(question, answer, source, target):
                raise translation_service.TranslationError("down")

            patch_translate_qa(scoped, _fail)
        created = admin_client.post(
            QUESTIONS, json={"question": question, "answer": "回答"}
        )
    assert created.status_code == 201
    return created.json()["id"]


def test_related_hides_untranslated_rows_and_translates_them(
    admin_client, client, db, monkeypatch
):
    current = _create(admin_client, "力ってなに？", True, monkeypatch)
    other = _create(admin_client, "運動ってなに？", False, monkeypatch)

    first = client.get(f"{QUESTIONS}/{current}/related", params={"lang": "en"}).json()
    assert other not in [item["id"] for item in first]

    # The background task ran after the response and stored the translation.
    db.expire_all()
    assert db.get(Question, other).question_en == "[en] 運動ってなに？"

    second = client.get(f"{QUESTIONS}/{current}/related", params={"lang": "en"}).json()
    assert "[en] 運動ってなに？" in [item["question"] for item in second]


def test_concepts_without_a_name_in_lang_are_hidden_from_students(
    admin_client, client, monkeypatch
):
    current = _create(admin_client, "力ってなに？", True, monkeypatch)

    admin = admin_client.get(f"{QUESTIONS}/{current}", params={"lang": "en"}).json()
    student = client.get(f"{QUESTIONS}/{current}", params={"lang": "en"}).json()

    assert student["concepts"] == ["concept A"]
    assert sorted(admin["concepts"]) == ["concept A", "概念B"]


def test_prerequisites_never_return_the_other_language(
    admin_client, client, db, monkeypatch
):
    current = _create(admin_client, "なぜ物体は加速するの？", True, monkeypatch)
    definer = _create(admin_client, "概念Aってなに？", False, monkeypatch)

    body = client.get(
        f"{QUESTIONS}/{current}/prerequisites", params={"lang": "en"}
    ).json()

    assert definer not in [item["id"] for item in body["items"]]
    # 概念B has no English name, so it is not shown as a gap either.
    assert body["gaps"] == ["concept A"]

    db.expire_all()
    assert db.get(Question, definer).question_en is not None
    again = client.get(
        f"{QUESTIONS}/{current}/prerequisites", params={"lang": "en"}
    ).json()
    assert [item["id"] for item in again["items"]] == [definer]


def test_admin_keeps_the_fallback(admin_client, monkeypatch):
    current = _create(admin_client, "力ってなに？", True, monkeypatch)
    other = _create(admin_client, "運動ってなに？", False, monkeypatch)

    related = admin_client.get(
        f"{QUESTIONS}/{current}/related", params={"lang": "en"}
    ).json()

    assert "運動ってなに？" in [item["question"] for item in related]
    assert other in [item["id"] for item in related]


@pytest.mark.anyio
async def test_background_translation_skips_rows_that_are_not_approved(db):
    unreviewed = Question(
        question_ja="未承認",
        answer_ja="回答",
        ja_provenance="ORIGINAL",
        status="UNREVIEWED",
    )
    db.add(unreviewed)
    db.commit()

    await background_translation_service.translate_missing([unreviewed.id])

    db.expire_all()
    assert db.get(Question, unreviewed.id).question_en is None
    # The claim is released even when the row is skipped, or the row
    # could never be picked up again once it is approved ([75]).
    assert db.query(BackgroundClaim).count() == 0


def test_concept_name_missing_in_lang_is_translated_once(
    admin_client, client, db, monkeypatch
):
    current = _create(admin_client, "力ってなに？", True, monkeypatch)
    calls: list[str] = []

    def _translate(question, answer, source, target):
        calls.append(question)
        return f"[{target}] {question}", f"[{target}] {answer}"

    patch_translate_qa(monkeypatch, _translate)

    first = client.get(f"{QUESTIONS}/{current}", params={"lang": "en"}).json()
    assert first["concepts"] == ["concept A"]

    second = client.get(f"{QUESTIONS}/{current}", params={"lang": "en"}).json()
    assert sorted(second["concepts"]) == ["[en] 概念B", "concept A"]
    # Only the missing name was sent to the translator, and only once.
    assert calls == ["概念B"]


def test_translated_concept_word_may_equal_another_senses_word(
    admin_client, client, db, monkeypatch
):
    # Two senses sharing an English word is now legal ([55]), so the
    # translation is stored instead of being dropped as a collision.
    current = _create(admin_client, "力ってなに？", True, monkeypatch)
    seen: list[tuple[str, str]] = []

    def _translate(question, answer, source, target):
        seen.append((question, answer))
        return "concept A", "context"

    patch_translate_qa(monkeypatch, _translate)

    client.get(f"{QUESTIONS}/{current}", params={"lang": "en"})
    again = client.get(f"{QUESTIONS}/{current}", params={"lang": "en"}).json()

    assert again["concepts"] == ["concept A", "concept A"]
    # The translator got a question using the concept as context.
    assert seen == [("概念B", "力ってなに？")]
