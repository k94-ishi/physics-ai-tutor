"""Behaviour of the bilingual question rows and the English mode."""

import pytest

from physics_ai_tutor.models import Question, QuestionEmbedding
from physics_ai_tutor.services import deepseek_service, translation_service
from physics_ai_tutor.services.translation_service import (
    translate_qa as real_translate_qa,
)
from tests.conftest import fake_generation

QUESTIONS = "/api/v1/questions"
REJECT_BODY = {"action": "REJECT", "reason": "PHYSICS_ERROR"}
ASK = "/api/v1/ai/ask"


def _embedding_languages(db, question_id: int) -> list[str]:
    rows = (
        db.query(QuestionEmbedding.language)
        .filter(QuestionEmbedding.question_id == question_id)
        .all()
    )
    return sorted({lang for (lang,) in rows})


# --- creation ---------------------------------------------------------------


def test_create_question_is_translated_eagerly(admin_client, db):
    response = admin_client.post(
        QUESTIONS, json={"question": "速度ってなに？", "answer": "向きを含む速さ。"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["original_language"] == "ja"
    assert body["available_languages"] == ["ja", "en"]
    assert body["texts"]["ja"]["provenance"] == "ORIGINAL"
    assert body["texts"]["en"]["provenance"] == "MACHINE"
    assert body["texts"]["en"]["question"] == "[en] 速度ってなに？"
    assert _embedding_languages(db, body["id"]) == ["en", "ja"]


def test_create_question_in_english_translates_to_japanese(admin_client):
    response = admin_client.post(
        QUESTIONS,
        json={
            "question": "What is velocity?",
            "answer": "Speed with direction.",
            "language": "en",
        },
    )

    body = response.json()
    assert body["original_language"] == "en"
    assert body["texts"]["ja"]["question"] == "[ja] What is velocity?"
    assert body["texts"]["ja"]["provenance"] == "MACHINE"


def test_create_question_with_both_languages_keeps_human_translation(admin_client):
    response = admin_client.post(
        QUESTIONS,
        json={
            "question_ja": "加速度ってなに？",
            "answer_ja": "速度の変化率。",
            "question_en": "What is acceleration?",
            "answer_en": "The rate of change of velocity.",
        },
    )

    body = response.json()
    assert body["original_language"] == "ja"
    assert body["texts"]["en"]["question"] == "What is acceleration?"
    assert body["texts"]["en"]["provenance"] == "HUMAN"


def test_create_question_rejects_half_pair(admin_client):
    response = admin_client.post(QUESTIONS, json={"question_ja": "質問だけ"})

    assert response.status_code == 422


def test_create_question_survives_translation_failure(admin_client, monkeypatch):
    def _fail(question, answer, source, target):
        raise translation_service.TranslationError("down")

    monkeypatch.setattr(translation_service, "translate_qa", _fail)

    response = admin_client.post(
        QUESTIONS, json={"question": "翻訳失敗でも保存", "answer": "回答"}
    )

    assert response.status_code == 201
    assert response.json()["available_languages"] == ["ja"]


def test_duplicate_is_detected_per_language(admin_client):
    admin_client.post(QUESTIONS, json={"question": "重複質問", "answer": "回答"})

    # Same text in the other language column is a different question.
    response = admin_client.post(
        QUESTIONS, json={"question": "重複質問", "answer": "回答", "language": "en"}
    )

    assert response.status_code == 201


# --- reading in a language --------------------------------------------------


def test_lang_parameter_resolves_text_and_falls_back(admin_client, client):
    created = admin_client.post(
        QUESTIONS, json={"question": "力ってなに？", "answer": "物体を加速させるもの。"}
    ).json()

    en = client.get(f"{QUESTIONS}/{created['id']}", params={"lang": "en"}).json()
    assert en["language"] == "en"
    assert en["question"] == "[en] 力ってなに？"
    assert en["provenance"] == "MACHINE"

    ja = client.get(f"{QUESTIONS}/{created['id']}").json()
    assert ja["language"] == "ja"
    assert ja["question"] == "力ってなに？"


def test_public_list_only_shows_rows_with_requested_language(
    admin_client, client, monkeypatch
):
    # One row translated, one row where translation failed.
    admin_client.post(QUESTIONS, json={"question": "翻訳あり", "answer": "回答"})

    def _fail(question, answer, source, target):
        raise translation_service.TranslationError("down")

    monkeypatch.setattr(translation_service, "translate_qa", _fail)
    admin_client.post(QUESTIONS, json={"question": "翻訳なし", "answer": "回答"})

    public_en = client.get(QUESTIONS, params={"lang": "en"}).json()
    admin_en = admin_client.get(QUESTIONS, params={"lang": "en"}).json()

    assert [item["question"] for item in public_en["items"]] == ["[en] 翻訳あり"]
    # Admins see every row; untranslated text falls back to the original.
    assert sorted(item["question"] for item in admin_en["items"]) == [
        "[en] 翻訳あり",
        "翻訳なし",
    ]


def test_exact_match_uses_the_requested_language_column(admin_client, client):
    admin_client.post(QUESTIONS, json={"question": "仕事ってなに？", "answer": "回答"})

    en = client.get(
        f"{QUESTIONS}/exact-match",
        params={"question": "[en] 仕事ってなに？", "lang": "en"},
    )
    ja_miss = client.get(
        f"{QUESTIONS}/exact-match", params={"question": "[en] 仕事ってなに？"}
    )

    assert en.status_code == 200
    assert en.json()["language"] == "en"
    assert ja_miss.status_code == 404


def test_detail_translates_lazily_for_legacy_rows(admin_client, client, db):
    # Simulate a row approved before translation existed.
    legacy = Question(
        question_ja="古い質問", answer_ja="古い回答", ja_provenance="ORIGINAL"
    )
    db.add(legacy)
    db.commit()

    response = client.get(f"{QUESTIONS}/{legacy.id}", params={"lang": "en"})

    assert response.status_code == 200
    assert response.json()["question"] == "[en] 古い質問"
    db.refresh(legacy)
    assert legacy.en_provenance == "MACHINE"
    assert _embedding_languages(db, legacy.id) == ["en"]


def test_keyword_search_matches_either_language(admin_client):
    admin_client.post(QUESTIONS, json={"question": "運動量とは", "answer": "回答"})

    response = admin_client.get(QUESTIONS, params={"keyword": "[en] 運動量"})

    assert response.json()["total"] == 1


# --- ask flow ---------------------------------------------------------------


def test_ask_in_english_uses_english_prompt_and_translates_in_background(
    client, admin_client, monkeypatch, db
):
    prompts_seen = []

    def _chat(system_prompt, user_prompt):
        prompts_seen.append(system_prompt)
        return "An answer."

    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        lambda s, u: fake_generation(_chat(s, u))(s, u),
    )

    response = client.post(
        ASK, json={"question": "What is momentum?", "language": "en"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"
    assert body["cached"] is False
    assert "You teach physics" in prompts_seen[0]

    saved = db.query(Question).filter(Question.id == body["question_id"]).one()
    db.refresh(saved)
    assert saved.original_language == "en"
    assert saved.status == "UNREVIEWED"
    # Background task has run by the time TestClient returns.
    assert saved.question_ja == "[ja] What is momentum?"
    assert saved.ja_provenance == "MACHINE"
    assert _embedding_languages(db, saved.id) == ["en", "ja"]


def test_ask_serves_cached_answer_including_unreviewed(client, monkeypatch):
    calls = []

    def _chat(system_prompt, user_prompt):
        calls.append(user_prompt)
        return "初回の回答"

    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        lambda s, u: fake_generation(_chat(s, u))(s, u),
    )

    first = client.post(ASK, json={"question": "キャッシュされる質問"}).json()
    second = client.post(ASK, json={"question": "キャッシュされる質問"}).json()

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["answer"] == "初回の回答"
    assert second["status"] == "UNREVIEWED"
    assert second["question_id"] == first["question_id"]
    assert len(calls) == 1


def test_ask_cache_hits_translated_text_of_other_language_row(
    client, admin_client, monkeypatch
):
    admin_client.post(
        QUESTIONS, json={"question": "位置エネルギーとは", "answer": "回答"}
    )

    def _chat(system_prompt, user_prompt):
        raise AssertionError("should be served from cache")

    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        lambda s, u: fake_generation(_chat(s, u))(s, u),
    )

    response = client.post(
        ASK, json={"question": "[en] 位置エネルギーとは", "language": "en"}
    )

    assert response.json()["cached"] is True
    assert response.json()["status"] == "APPROVED"


def test_ask_does_not_serve_rejected_answer(client, admin_client, monkeypatch):
    monkeypatch.setattr(
        deepseek_service, "generate_answer", fake_generation("最初の回答")
    )
    first = client.post(ASK, json={"question": "却下される質問です"}).json()
    admin_client.post(
        f"{QUESTIONS}/{first['question_id']}/review",
        json=REJECT_BODY,
    )

    monkeypatch.setattr(
        deepseek_service, "generate_answer", fake_generation("二回目の回答")
    )
    second = client.post(ASK, json={"question": "却下される質問です"}).json()

    assert second["cached"] is False
    assert second["answer"] == "二回目の回答"


# --- review and edits -------------------------------------------------------


def test_review_in_english_records_language_and_refreshes_machine_japanese(
    client, admin_client, monkeypatch, db
):
    monkeypatch.setattr(deepseek_service, "generate_answer", fake_generation("Answer."))
    asked = client.post(
        ASK, json={"question": "What is work in physics?", "language": "en"}
    ).json()
    question_id = asked["question_id"]

    response = admin_client.post(
        f"{QUESTIONS}/{question_id}/review",
        params={"lang": "en"},
        json={
            "action": "EDIT_APPROVE",
            "reason": "INCOMPLETE",
            "language": "en",
            "question": "What is work in physics?",
            "answer": "Force times displacement.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["answer"] == "Force times displacement."
    # The machine-made Japanese side was regenerated from the edited text.
    assert body["texts"]["ja"]["answer"] == "[ja] Force times displacement."

    history = admin_client.get(f"{QUESTIONS}/{question_id}/reviews").json()
    assert history[0]["language"] == "en"
    assert history[0]["before_answer"] == "Answer."
    assert history[0]["after_answer"] == "Force times displacement."


def test_edit_keeps_human_translation(admin_client):
    created = admin_client.post(
        QUESTIONS,
        json={
            "question_ja": "質問",
            "answer_ja": "回答",
            "question_en": "Question",
            "answer_en": "Human answer",
        },
    ).json()

    updated = admin_client.put(
        f"{QUESTIONS}/{created['id']}",
        json={"question": "質問", "answer": "更新された回答"},
    ).json()

    assert updated["texts"]["ja"]["answer"] == "更新された回答"
    assert updated["texts"]["en"]["answer"] == "Human answer"
    assert updated["texts"]["en"]["provenance"] == "HUMAN"


def test_edit_refreshes_machine_translation(admin_client):
    created = admin_client.post(
        QUESTIONS, json={"question": "質問", "answer": "回答"}
    ).json()

    updated = admin_client.put(
        f"{QUESTIONS}/{created['id']}",
        json={"question": "質問", "answer": "更新された回答"},
    ).json()

    assert updated["texts"]["en"]["answer"] == "[en] 更新された回答"
    assert updated["texts"]["en"]["provenance"] == "MACHINE"


# --- translate endpoint and import ------------------------------------------


def test_translate_endpoint_fills_missing_language(admin_client, db):
    legacy = Question(question_ja="未翻訳", answer_ja="回答", ja_provenance="ORIGINAL")
    db.add(legacy)
    db.commit()

    response = admin_client.post(
        f"{QUESTIONS}/translate", json={"question_ids": [legacy.id, 99999]}
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert {"question_id": legacy.id, "success": True, "language": "en"} in results
    assert {"question_id": 99999, "success": False, "language": None} in results


def test_import_accepts_explicit_language_columns(admin_client):
    content = "\n".join(
        [
            '{"question": "レガシー形式", "answer": "回答"}',
            '{"question_en": "English only", "answer_en": "Answer"}',
            '{"question_ja": "両方", "answer_ja": "回答", '
            '"question_en": "Both", "answer_en": "Answer"}',
        ]
    )
    response = admin_client.post(
        f"{QUESTIONS}/import",
        data={"status": "APPROVED", "source": "MANUAL"},
        files={"file": ("q.jsonl", content, "application/jsonl")},
    )

    assert response.status_code == 201
    created = response.json()["questions"]
    assert [q["original_language"] for q in created] == ["ja", "en", "ja"]
    assert all(q["available_languages"] == ["ja", "en"] for q in created)
    assert created[2]["texts"]["en"]["provenance"] == "HUMAN"


def test_translator_parses_marked_output(monkeypatch):
    monkeypatch.setattr(
        deepseek_service,
        "chat_completion",
        lambda s, u: "noise\n=====QUESTION=====\nQ\n=====ANSWER=====\nA\n",
    )

    assert real_translate_qa("q", "a", "ja", "en") == ("Q", "A")


def test_translator_rejects_malformed_output(monkeypatch):
    monkeypatch.setattr(deepseek_service, "chat_completion", lambda s, u: "garbage")

    with pytest.raises(translation_service.TranslationError):
        real_translate_qa("q", "a", "ja", "en")
