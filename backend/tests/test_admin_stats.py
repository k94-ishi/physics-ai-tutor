from datetime import UTC, datetime, timedelta

from physics_ai_tutor.models import Question, QuestionAsk
from physics_ai_tutor.services import deepseek_service
from tests.conftest import fake_generation

STATS_PATH = "/api/v1/admin/stats"
ASK_PATH = "/api/v1/ai/ask"


def _mock_answer(monkeypatch):
    monkeypatch.setattr(
        deepseek_service,
        "generate_answer",
        fake_generation("回答"),
    )


def test_stats_requires_admin(client, user_client):
    assert client.get(STATS_PATH).status_code == 401
    assert user_client.get(STATS_PATH).status_code == 403


def test_stats_counts_todays_activity(client, user_client, admin_client, monkeypatch):
    _mock_answer(monkeypatch)

    # One anonymous generation (no ask row), one signed-in generation,
    # and one signed-in cache hit on the anonymous question.
    assert client.post(ASK_PATH, json={"question": "匿名の統計質問"}).status_code == 200
    assert (
        user_client.post(ASK_PATH, json={"question": "会員の統計質問"}).status_code
        == 200
    )
    hit = user_client.post(ASK_PATH, json={"question": "匿名の統計質問"})
    assert hit.json()["cached"] is True

    body = admin_client.get(STATS_PATH).json()
    today = body["daily"][-1]

    assert body["days"] == 14
    assert len(body["daily"]) == 14
    assert today["generations"] == 2
    assert today["asks"] == 2
    assert today["cache_hits"] == 1
    assert today["distinct_users"] == 1
    assert body["unreviewed_count"] == 2
    assert body["unreviewed_median_age_days"] is not None
    assert body["unreviewed_median_age_days"] < 1
    # The anonymous ask consumed the single shared test IP bucket.
    assert body["anonymous_ip_buckets_24h"] == 1


def test_ask_rows_carry_the_cache_hit_flag(user_client, db, monkeypatch):
    _mock_answer(monkeypatch)

    user_client.post(ASK_PATH, json={"question": "フラグテスト質問"})
    user_client.post(ASK_PATH, json={"question": "フラグテスト質問"})

    flags = [ask.cache_hit for ask in db.query(QuestionAsk).order_by(QuestionAsk.id)]

    assert flags == [False, True]


def test_stats_days_parameter_controls_window(admin_client, db, monkeypatch):
    _mock_answer(monkeypatch)

    # A generation 3 days ago falls outside a 2-day window.
    old = Question(
        question_ja="古い質問",
        answer_ja="古い回答",
        original_language="ja",
        ja_provenance="ORIGINAL",
        status="UNREVIEWED",
        source="AI_GENERATED",
        created_at=datetime.now(UTC) - timedelta(days=3),
    )
    db.add(old)
    db.commit()

    narrow = admin_client.get(STATS_PATH, params={"days": 2}).json()
    wide = admin_client.get(STATS_PATH, params={"days": 7}).json()

    assert sum(day["generations"] for day in narrow["daily"]) == 0
    assert sum(day["generations"] for day in wide["daily"]) == 1


def test_stats_empty_database(admin_client):
    body = admin_client.get(STATS_PATH).json()

    assert body["unreviewed_count"] == 0
    assert body["unreviewed_median_age_days"] is None
    assert all(day["asks"] == 0 for day in body["daily"])


def test_stats_unlinked_asks_do_not_count_as_users(
    user_client, admin_client, db, monkeypatch
):
    _mock_answer(monkeypatch)

    user_client.post(ASK_PATH, json={"question": "退会前の統計質問"})
    db.query(QuestionAsk).update({"user_id": None})
    db.commit()

    today = admin_client.get(STATS_PATH).json()["daily"][-1]

    assert today["asks"] == 1
    assert today["distinct_users"] == 0
