"""Students never read the other language on the question page ([53])."""

from physics_ai_tutor.models import Question
from physics_ai_tutor.services import (
    background_translation_service,
    translation_service,
)

QUESTIONS = "/api/v1/questions"


def _create(admin_client, question: str, translate: bool, monkeypatch) -> int:
    # The mocked extractor links every row to 概念A (has English) and 概念B (has not).
    with monkeypatch.context() as scoped:
        if not translate:

            def _fail(question, answer, source, target):
                raise translation_service.TranslationError("down")

            scoped.setattr(translation_service, "translate_qa", _fail)
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

    student = client.get(f"{QUESTIONS}/{current}", params={"lang": "en"}).json()
    admin = admin_client.get(f"{QUESTIONS}/{current}", params={"lang": "en"}).json()

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


def test_background_translation_skips_rows_that_are_not_approved(db):
    unreviewed = Question(
        question_ja="未承認",
        answer_ja="回答",
        ja_provenance="ORIGINAL",
        status="UNREVIEWED",
    )
    db.add(unreviewed)
    db.commit()

    claimed = background_translation_service.claim([unreviewed.id])
    background_translation_service.translate_missing(claimed)

    db.expire_all()
    assert db.get(Question, unreviewed.id).question_en is None


def test_claim_deduplicates_rows_in_flight():
    first = background_translation_service.claim([901, 902, 901])
    second = background_translation_service.claim([902, 903])
    background_translation_service.translate_missing([])

    assert first == [901, 902]
    assert second == [903]

    # Release so other tests start clean.
    for question_id in (901, 902, 903):
        background_translation_service._release(question_id)
