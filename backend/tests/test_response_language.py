"""One value decides a response's language rules ([62])."""

from physics_ai_tutor.models import Question
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.services.response_language import (
    ResponseLanguage,
    TranslationNeeds,
)


def _row(question_id: int, en: bool) -> Question:
    row = Question(id=question_id, question_ja="質問", answer_ja="回答")
    if en:
        row.question_en, row.answer_en = "Q", "A"
    return row


def test_students_are_strict_and_admins_fall_back():
    assert ResponseLanguage.for_caller("en", admin=False).strict
    assert not ResponseLanguage.for_caller("en", admin=True).strict


def test_a_plain_language_means_the_admin_fallback():
    assert ResponseLanguage.of("ja") == ResponseLanguage(Language.JA, strict=False)
    strict = ResponseLanguage(Language.EN, strict=True)
    assert ResponseLanguage.of(strict) is strict


def test_strict_readers_lose_rows_without_their_language():
    rows = [_row(1, en=True), _row(2, en=False)]

    kept, missing = ResponseLanguage(Language.EN, strict=True).readable(rows)
    all_rows, none = ResponseLanguage(Language.EN).readable(rows)

    assert [r.id for r in kept] == [1] and missing == [2]
    assert all_rows == rows and none == []


def test_needs_merge_keeps_order():
    merged = TranslationNeeds([1], [10]).merge(TranslationNeeds([2], [20]))

    assert merged == TranslationNeeds([1, 2], [10, 20])
