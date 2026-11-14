"""Concepts as senses with many words per language ([55])."""

import pytest

from physics_ai_tutor.core.text import normalize_key
from physics_ai_tutor.models import Concept, ConceptTerm, Question, QuestionConcept
from tests.conftest import (
    async_engine,
    attach_concepts,
    engine,
    patch_create_embeddings,
    patch_extract_concept_names,
)

CONCEPTS = "/api/v1/concepts"
ADMIN = "/api/v1/admin/concepts"
QUESTIONS = "/api/v1/questions"


def _axis(index: int) -> list[float]:
    vector = [0.0] * 1536
    vector[index] = 1.0
    return vector


# Pair text -> meaning axis. Same axis = same meaning (cosine 1), else 0.
MEANINGS = {
    "位相 | phase": 1,
    "相 | phase": 2,
    "位相 | topology": 3,
    "速度 | velocity": 4,
    "速度 | speed": 4,
    "速さ | speed": 5,
}


@pytest.fixture(autouse=True)
def _meaning_embeddings(monkeypatch):
    calls: list[list[str]] = []

    def _embed(texts):
        calls.append(list(texts))
        return [_axis(MEANINGS.get(text, 0)) for text in texts]

    patch_create_embeddings(monkeypatch, _embed)
    return calls


def _question(db, text: str, status: str = "APPROVED", en: str | None = None):
    question = Question(
        question_ja=text,
        answer_ja="回答",
        ja_provenance="ORIGINAL",
        question_en=en,
        answer_en="answer" if en else None,
        en_provenance="MACHINE" if en else None,
        status=status,
    )
    db.add(question)
    db.flush()
    return question


def _tag(db, question, *pairs: str) -> list[Concept]:
    # The async attach runs in its own session; it must see the row.
    db.commit()
    return attach_concepts(db, question.id, list(pairs))


def _words(concept: Concept, language: str) -> list[tuple[str, bool]]:
    return sorted((t.term, t.is_preferred) for t in concept.terms_in(language))


# --- matching -----------------------------------------------------------------


def test_same_english_word_different_meaning_makes_two_senses(db):
    wave = _tag(db, _question(db, "波の位相とは？"), "位相 | phase")[0]
    matter = _tag(db, _question(db, "気相とは？"), "相 | phase")[0]

    assert wave.id != matter.id
    assert _words(matter, "en") == [("phase", True)]


def test_same_japanese_word_different_meaning_makes_two_senses(db):
    wave = _tag(db, _question(db, "波の位相とは？"), "位相 | phase")[0]
    topology = _tag(db, _question(db, "トポロジーとは？"), "位相 | topology")[0]

    assert wave.id != topology.id


def test_synonym_becomes_an_alias_of_the_same_sense(db):
    velocity = _tag(db, _question(db, "速度とは？"), "速度 | velocity")[0]
    again = _tag(db, _question(db, "速度の向きは？"), "速度 | speed")[0]

    assert again.id == velocity.id
    db.refresh(velocity)
    # The first word stays the label; the new one is an alias.
    assert _words(velocity, "en") == [("speed", False), ("velocity", True)]
    assert velocity.name_en == "velocity"


def test_both_words_known_needs_no_embedding_call(db, _meaning_embeddings):
    first = _tag(db, _question(db, "位相とは？"), "位相 | phase")[0]
    _meaning_embeddings.clear()

    second = _tag(db, _question(db, "位相差とは？"), "位相 | phase")[0]

    assert second.id == first.id
    assert _meaning_embeddings == []


def test_one_sided_pair_joins_the_only_sense_with_that_word(db):
    first = _tag(db, _question(db, "位相とは？"), "位相 | phase")[0]
    second = _tag(db, _question(db, "位相のずれは？"), "位相")[0]

    assert second.id == first.id


# --- search and filter ----------------------------------------------------------


def _speed_corpus(db):
    _tag(db, _question(db, "速さとは？", en="What is speed?"), "速さ | speed")
    _tag(db, _question(db, "速度とは？", en="What is velocity?"), "速度 | velocity")
    _tag(db, _question(db, "速度の向きは？", en="Direction?"), "速度 | speed")


def test_search_offers_every_sense_of_a_shared_word(client, db):
    _tag(db, _question(db, "波の位相とは？", en="Wave phase?"), "位相 | phase")
    _tag(db, _question(db, "気相とは？", en="Gas phase?"), "相 | phase")

    body = client.get(CONCEPTS, params={"q": "phase", "lang": "en"}).json()

    assert [item["label"] for item in body] == ["phase", "phase"]
    assert {item["matched_term"] for item in body} == {"phase"}


def test_search_ranks_the_preferred_word_above_an_alias(client, db):
    _speed_corpus(db)

    body = client.get(CONCEPTS, params={"q": "speed", "lang": "en"}).json()

    assert [item["label"] for item in body] == ["speed", "velocity"]


def test_search_in_japanese_ui_with_an_english_word(client, db):
    _speed_corpus(db)

    body = client.get(CONCEPTS, params={"q": "velocity", "lang": "ja"}).json()

    assert [item["label"] for item in body] == ["速度"]
    assert body[0]["question_count"] == 2


def test_public_search_hides_senses_without_approved_questions(
    client, admin_client, db
):
    _tag(db, _question(db, "未承認の位相", status="UNREVIEWED"), "位相 | phase")

    assert client.get(CONCEPTS, params={"q": "phase"}).json() == []
    assert len(admin_client.get(CONCEPTS, params={"q": "phase"}).json()) == 1


def test_list_by_word_finds_questions_of_every_sense_and_either_language(client, db):
    _speed_corpus(db)

    # An English word finds Japanese-only rows too, through the sense.
    by_word = client.get(QUESTIONS, params={"concept": "speed"}).json()
    by_id = client.get(
        QUESTIONS,
        params={"concept_id": db.query(Concept).filter_by(name_ja="速さ").one().id},
    ).json()

    assert sorted(q["question"] for q in by_word["items"]) == [
        "速さとは？",
        "速度とは？",
        "速度の向きは？",
    ]
    assert [q["question"] for q in by_id["items"]] == ["速さとは？"]


# --- admin editor -------------------------------------------------------------


def test_admin_endpoints_require_admin(client, user_client):
    assert client.get(ADMIN).status_code == 401
    assert user_client.get(ADMIN).status_code == 403


def test_admin_list_filters_shared_words(admin_client, db):
    wave = _tag(db, _question(db, "波の位相とは？"), "位相 | phase")[0]
    matter = _tag(db, _question(db, "気相とは？"), "相 | phase")[0]
    _tag(db, _question(db, "力とは？"), "力 | force")

    body = admin_client.get(ADMIN, params={"review_filter": "shared"}).json()

    assert sorted(item["id"] for item in body["items"]) == sorted([wave.id, matter.id])
    by_id = {item["id"]: item for item in body["items"]}
    assert by_id[wave.id]["shares_word_with"] == [matter.id]


def test_admin_detail_lists_questions_and_partners_and_404s(admin_client, db):
    question = _question(db, "波の位相とは？")
    wave = _tag(db, question, "位相 | phase")[0]
    matter = _tag(db, _question(db, "気相とは？"), "相 | phase")[0]

    body = admin_client.get(f"{ADMIN}/{wave.id}").json()

    assert [ref["id"] for ref in body["questions"]] == [question.id]
    assert body["shares_word_with"] == [matter.id]
    assert body["question_count"] == 1
    assert admin_client.get(f"{ADMIN}/999999").status_code == 404


def test_admin_adds_alias_and_changes_the_label(admin_client, db):
    concept = _tag(db, _question(db, "速度とは？"), "速度 | velocity")[0]

    added = admin_client.post(
        f"{ADMIN}/{concept.id}/terms",
        json={"language": "en", "term": "speed", "is_preferred": False},
    )
    speed = next(t for t in added.json()["terms"] if t["term"] == "speed")
    relabel = admin_client.patch(
        f"{ADMIN}/terms/{speed['id']}", json={"is_preferred": True}
    )
    duplicate = admin_client.post(
        f"{ADMIN}/{concept.id}/terms", json={"language": "en", "term": "Speed"}
    )

    assert added.status_code == 201
    assert speed["source"] == "TEACHER"
    preferred = [t["term"] for t in relabel.json()["terms"] if t["is_preferred"]]
    assert sorted(preferred) == ["speed", "速度"]
    db.expire_all()
    assert db.get(Concept, concept.id).name_en == "speed"
    # Same word modulo case and width is the same word.
    assert duplicate.status_code == 409


def test_deleting_the_label_promotes_the_next_word(admin_client, db):
    concept = _tag(db, _question(db, "速度とは？"), "速度 | velocity", "速度 | speed")[
        0
    ]
    label = next(t for t in concept.terms if t.term == "velocity")

    assert admin_client.delete(f"{ADMIN}/terms/{label.id}").status_code == 204

    db.expire_all()
    assert db.get(Concept, concept.id).name_en == "speed"


def test_merge_moves_questions_and_words(admin_client, db):
    a = _tag(db, _question(db, "速さとは？"), "速さ | speed")[0]
    b = _tag(db, _question(db, "速度とは？"), "速度 | velocity")[0]
    # Read before the request: the route deletes the row in its own session.
    source_id = a.id

    body = admin_client.post(
        f"{ADMIN}/{source_id}/merge", json={"into_id": b.id}
    ).json()

    assert body["question_count"] == 2
    assert {t["term"] for t in body["terms"]} == {"速さ", "speed", "速度", "velocity"}
    db.expire_all()
    assert db.get(Concept, source_id) is None


def test_split_moves_the_chosen_questions_to_a_new_sense(admin_client, db):
    wave_q = _question(db, "波の位相とは？")
    matter_q = _question(db, "気相とは？")
    merged = _tag(db, wave_q, "位相 | phase")[0]
    # The old matching rule glued the states-of-matter QA on, like this.
    db.add(QuestionConcept(question_id=matter_q.id, concept_id=merged.id))
    db.commit()

    created = admin_client.post(
        f"{ADMIN}/{merged.id}/split",
        json={
            "question_ids": [matter_q.id],
            "terms": [
                {"language": "ja", "term": "相"},
                {"language": "en", "term": "phase"},
            ],
            "gloss_en": "state of matter",
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert [q["id"] for q in body["questions"]] == [matter_q.id]
    assert body["gloss_en"] == "state of matter"
    assert body["shares_word_with"] == [merged.id]
    remaining = admin_client.get(f"{ADMIN}/{merged.id}").json()["questions"]
    assert [q["id"] for q in remaining] == [wave_q.id]


def test_normalize_key_ignores_case_width_and_spacing():
    assert normalize_key("  Ｐｈａｓｅ   Shift ") == "phase shift"


def test_existing_terms_table_is_used_for_preferred_mirror(db):
    concept = _tag(db, _question(db, "力とは？"), "力 | force")[0]

    assert db.query(ConceptTerm).filter_by(concept_id=concept.id).count() == 2
    assert (concept.name_ja, concept.name_en) == ("力", "force")


# --- automatic split of old merges ---------------------------------------------


def test_split_cli_reattaches_glued_questions_to_their_own_sense(
    db, monkeypatch, capsys
):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy.orm import sessionmaker

    from physics_ai_tutor.cli import split_merged_concepts as cli

    # The CLI opens its own sessions against the test database.
    monkeypatch.setattr(
        cli, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False)
    )
    monkeypatch.setattr(
        cli,
        "AsyncSessionLocal",
        async_sessionmaker(bind=async_engine, expire_on_commit=False),
    )
    wave_q = _question(db, "波の位相とは？")
    matter_q = _question(db, "気相とは？")
    merged = _tag(db, wave_q, "位相 | phase")[0]
    db.add(QuestionConcept(question_id=matter_q.id, concept_id=merged.id))
    db.commit()
    patch_extract_concept_names(
        monkeypatch, lambda question, answer, language="ja": ["相 | phase"]
    )

    assert cli.main(dry_run=True) == 0
    assert "1 suspect links on 1 questions" in capsys.readouterr().out
    assert cli.main(force=True) == 0

    db.expire_all()
    links = {
        link.question_id: link.concept_id for link in db.query(QuestionConcept).all()
    }
    assert links[wave_q.id] == merged.id
    assert links[matter_q.id] != merged.id
    assert db.get(Concept, links[matter_q.id]).name_ja == "相"
    # Nothing suspect is left.
    assert cli.find_suspect_links(db) == []
