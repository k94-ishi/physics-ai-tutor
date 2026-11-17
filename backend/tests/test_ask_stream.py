"""Streamed answers over SSE ([71]).

The ask flow's own guarantees are covered by `test_ai.py`; these check
that streaming keeps them - above all that the off-topic sentinel never
reaches the student and that a declined question is still not saved.
"""

import json

import pytest

from physics_ai_tutor.core import prompts
from physics_ai_tutor.models import Question
from physics_ai_tutor.schemas.language import TextProvenance
from physics_ai_tutor.schemas.question import (
    QuestionSource,
    QuestionStatus,
)
from physics_ai_tutor.services import deepseek_service

STREAM_PATH = "/api/v1/ai/ask/stream"
ASK_PATH = "/api/v1/ai/ask"


def patch_stream(monkeypatch, pieces, model="mock-model"):
    """Stream `pieces` then the GenerationResult, as DeepSeek would."""

    async def _stream(system_prompt, user_prompt, max_tokens=None):
        for piece in pieces:
            yield piece
        yield deepseek_service.GenerationResult(
            content="".join(pieces),
            model=model,
            prompt_tokens=11,
            completion_tokens=22,
        )

    monkeypatch.setattr(deepseek_service, "stream_answer", _stream)


def parse_events(body: str) -> list[tuple[str, dict]]:
    """[(event name, payload), ...] from an SSE body."""
    events = []
    for frame in body.split("\n\n"):
        if not frame.strip():
            continue
        name = next(
            line[len("event: ") :]
            for line in frame.splitlines()
            if line.startswith("event: ")
        )
        data = next(
            line[len("data: ") :]
            for line in frame.splitlines()
            if line.startswith("data: ")
        )
        events.append((name, json.loads(data)))
    return events


def deltas(events) -> str:
    return "".join(payload["text"] for name, payload in events if name == "delta")


def done(events) -> dict:
    return next(payload for name, payload in events if name == "done")


def test_stream_sends_the_answer_in_pieces_then_the_metadata(client, monkeypatch, db):
    patch_stream(monkeypatch, ["加速度とは", "速度の変化率", "です。"])

    response = client.post(STREAM_PATH, json={"question": "加速度とは何ですか"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_events(response.text)

    assert [name for name, _ in events] == ["delta", "delta", "delta", "done"]
    assert deltas(events) == "加速度とは速度の変化率です。"

    final = done(events)
    assert final["answer"] == "加速度とは速度の変化率です。"
    assert final["status"] == QuestionStatus.UNREVIEWED
    assert final["cached"] is False

    saved = db.get(Question, final["question_id"])
    assert saved is not None
    assert saved.answer_ja == "加速度とは速度の変化率です。"


def test_streamed_row_matches_what_the_plain_endpoint_would_save(
    client, monkeypatch, db
):
    """Same row, whichever endpoint produced it."""
    patch_stream(monkeypatch, ["ストリーム", "回答"])

    response = client.post(STREAM_PATH, json={"question": "保存比較のための質問"})
    question_id = done(parse_events(response.text))["question_id"]

    saved = db.get(Question, question_id)

    assert saved.status == QuestionStatus.UNREVIEWED
    assert saved.source == QuestionSource.AI_GENERATED
    assert saved.generation_model == "mock-model"
    assert saved.prompt_version == prompts.ANSWER_PROMPT_VERSION
    assert saved.generation_mode == "DIRECT"
    assert saved.prompt_tokens == 11
    assert saved.completion_tokens == 22


def test_a_cache_hit_streams_the_stored_answer_without_generating(
    client, monkeypatch, db
):
    db.add(
        Question(
            question_ja="キャッシュ済みの質問です",
            answer_ja="キャッシュ済みの回答",
            ja_provenance=TextProvenance.ORIGINAL,
            original_language="ja",
            status=QuestionStatus.APPROVED,
            source=QuestionSource.MANUAL,
        )
    )
    db.commit()

    def _never(*args, **kwargs):
        raise AssertionError("a cache hit must not call DeepSeek")

    monkeypatch.setattr(deepseek_service, "stream_answer", _never)

    response = client.post(STREAM_PATH, json={"question": "キャッシュ済みの質問です"})
    events = parse_events(response.text)

    assert deltas(events) == "キャッシュ済みの回答"
    assert done(events)["cached"] is True


@pytest.mark.parametrize(
    "pieces",
    [
        # The sentinel arrives whole, split across chunks, or one character
        # at a time - the student must see none of it in any case.
        [f"{prompts.OFF_TOPIC_SENTINEL} 物理の質問をしてください。"],
        ["[OFF_", "TOPIC]", " 物理の質問をしてください。"],
        list(f"{prompts.OFF_TOPIC_SENTINEL} 物理の質問をしてください。"),
        ["  ", prompts.OFF_TOPIC_SENTINEL, "物理の質問をしてください。"],
    ],
)
def test_an_off_topic_refusal_never_leaks_the_sentinel(client, monkeypatch, db, pieces):
    patch_stream(monkeypatch, pieces)

    response = client.post(STREAM_PATH, json={"question": "今日の天気はどうですか"})
    events = parse_events(response.text)
    text = deltas(events)

    assert prompts.OFF_TOPIC_SENTINEL not in text
    assert prompts.OFF_TOPIC_SENTINEL not in json.dumps(events, ensure_ascii=False)
    assert "物理の質問をしてください。" in text

    final = done(events)
    assert final["question_id"] is None
    # Declined answers never enter the knowledge base ([70] / security.md).
    assert db.query(Question).count() == 0


def test_a_declined_question_still_spends_quota(client, monkeypatch, db):
    """The LLM call happened, so the ask is counted, as on `/ask`."""
    from physics_ai_tutor.models import RateLimitHit

    patch_stream(
        monkeypatch, [f"{prompts.OFF_TOPIC_SENTINEL} 物理の質問をしてください。"]
    )

    client.post(STREAM_PATH, json={"question": "今日の天気はどうですか"})

    assert db.query(RateLimitHit).count() == 1


def test_a_short_answer_below_the_sentinel_length_is_still_sent(
    client, monkeypatch, db
):
    """A reply shorter than `[OFF_TOPIC]` must not be swallowed."""
    patch_stream(monkeypatch, ["はい"])

    response = client.post(STREAM_PATH, json={"question": "短い答えになる質問です"})

    assert deltas(parse_events(response.text)) == "はい"


def test_an_answer_starting_like_the_sentinel_is_not_mistaken_for_one(
    client, monkeypatch, db
):
    """`[OFF...` is only a refusal when it is the whole sentinel."""
    patch_stream(monkeypatch, ["[OFF", "SIDE] ", "というラベルの話です。"])

    response = client.post(STREAM_PATH, json={"question": "ラベルについての質問"})
    text = deltas(parse_events(response.text))

    assert text == "[OFFSIDE] というラベルの話です。"
    assert done(parse_events(response.text))["question_id"] is not None


def test_generation_failure_arrives_as_an_error_event(client, monkeypatch, db):
    """The status line is already 200, so a failure cannot be a 503."""
    from physics_ai_tutor.core.exceptions import DeepSeekGenerationError

    async def _fail(system_prompt, user_prompt, max_tokens=None):
        raise DeepSeekGenerationError("boom")
        yield ""  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(deepseek_service, "stream_answer", _fail)

    response = client.post(STREAM_PATH, json={"question": "失敗する質問です"})
    events = parse_events(response.text)

    assert response.status_code == 200
    assert [name for name, _ in events] == ["error"]
    assert "DeepSeek" in events[0][1]["detail"]
    assert db.query(Question).count() == 0


def test_the_stream_respects_the_rate_limit(client, monkeypatch, db):
    patch_stream(monkeypatch, ["回答"])

    for index in range(3):
        assert (
            client.post(
                STREAM_PATH, json={"question": f"制限テストの質問 {index} です"}
            ).status_code
            == 200
        )

    # Anonymous callers get three asks an hour; the fourth is refused
    # before the stream starts, so it is a plain 429.
    refused = client.post(STREAM_PATH, json={"question": "制限を超える質問です"})

    assert refused.status_code == 429


def test_the_plain_endpoint_still_works(client, monkeypatch, db):
    """`/ask` is unchanged; admin tools and the fallback still use it."""
    from tests.conftest import fake_generation, patch_generation

    patch_generation(monkeypatch, fake_generation("通常の回答"))

    response = client.post(ASK_PATH, json={"question": "通常の経路の質問です"})

    assert response.status_code == 200
    assert response.json()["answer"] == "通常の回答"


def test_post_generation_tasks_run_after_the_stream(client, monkeypatch, db):
    """Translation still happens, just after the answer has been sent."""
    patch_stream(monkeypatch, ["翻訳される", "回答"])

    response = client.post(STREAM_PATH, json={"question": "翻訳される質問です"})
    question_id = done(parse_events(response.text))["question_id"]

    saved = db.get(Question, question_id)
    db.refresh(saved)

    # The conftest fake translator marks its output.
    assert saved.question_en == "[en] 翻訳される質問です"
    assert saved.answer_en == "[en] 翻訳される回答"


@pytest.mark.anyio
async def test_abandoning_the_stream_saves_nothing(async_db, monkeypatch):
    """A client that walks away leaves no UNREVIEWED row behind ([71]).

    The row is written only after the whole answer has been collected,
    so this is tested where the invariant lives - on the generator -
    rather than through a transport whose cancellation semantics would
    make the test about httpx instead of about us.
    """
    from sqlalchemy import select

    from physics_ai_tutor.schemas.ai import AskAiRequest
    from physics_ai_tutor.services import ai_service

    patch_stream(monkeypatch, ["最初の断片", "二つ目", "三つ目"])

    recorded: list[bool] = []

    async def _record() -> None:
        recorded.append(True)

    saved: dict[str, int | None] = {"question_id": None}
    events = ai_service.ask_stream(
        async_db,
        AskAiRequest(question="途中で離脱される質問です"),
        user_id=None,
        record_generation=_record,
        rate_limit_bucket="ip:test",
        saved=saved,
    )

    first = await anext(events)
    assert first.kind == "delta"
    assert first.text == "最初の断片"

    # The student closed the tab.
    await events.aclose()

    assert saved["question_id"] is None
    assert (await async_db.scalars(select(Question))).all() == []
    # The generation did happen, so the quota stays spent.
    assert recorded == [True]
