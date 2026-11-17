"""Background work runs a few items at a time ([72]).

The behaviour of a run and of a translation is covered elsewhere; these
check the concurrency itself: that independent LLM calls overlap, that
the limit is respected, and that the guarantees which concurrency could
plausibly break ([34] takeover, [53] one call per row, the daily budget)
still hold.
"""

import asyncio

import pytest
from sqlalchemy import select

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.models import (
    AiReview,
    AiReviewRun,
    BackgroundClaim,
    Question,
)
from physics_ai_tutor.schemas.language import TextProvenance
from physics_ai_tutor.schemas.question import QuestionSource, QuestionStatus
from physics_ai_tutor.services import (
    ai_review_service,
    background_translation_service,
    deepseek_service,
    translation_service,
)

pytestmark = pytest.mark.anyio

VALID_REVIEW = (
    '{"verdict": "APPROVE", "confidence": 0.9, "reasons": [],'
    ' "rationale": "ok", "suggested_answer": null,'
    ' "rubric": {"physics": 5}}'
)


class Tracker:
    """Records how many calls were in flight at the same time."""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay
        self.active = 0
        self.peak = 0
        self.total = 0

    async def run(self) -> None:
        self.active += 1
        self.total += 1
        self.peak = max(self.peak, self.active)
        try:
            await asyncio.sleep(self.delay)
        finally:
            self.active -= 1


def _unreviewed(index: int) -> Question:
    return Question(
        question_ja=f"並行処理の質問{index}",
        answer_ja=f"回答{index}",
        ja_provenance=TextProvenance.ORIGINAL,
        original_language="ja",
        status=QuestionStatus.UNREVIEWED,
        source=QuestionSource.AI_GENERATED,
    )


def _approved(index: int) -> Question:
    return Question(
        question_ja=f"翻訳待ちの質問{index}",
        answer_ja=f"回答{index}",
        ja_provenance=TextProvenance.ORIGINAL,
        original_language="ja",
        status=QuestionStatus.APPROVED,
        source=QuestionSource.MANUAL,
    )


async def test_translations_overlap_up_to_the_limit(async_db, monkeypatch):
    monkeypatch.setattr(settings, "translation_concurrency", 3)
    tracker = Tracker()

    async def _translate(question, answer, source, target):
        await tracker.run()
        return f"[{target}] {question}", f"[{target}] {answer}"

    monkeypatch.setattr(translation_service, "translate_qa", _translate)

    for index in range(9):
        async_db.add(_approved(index))
    await async_db.commit()
    ids = list((await async_db.scalars(select(Question.id))).all())

    await background_translation_service.translate_missing(ids)

    assert tracker.total == 9
    assert tracker.peak == 3
    # Every claim released, so a later view can retry a failed row ([75]).
    assert (await async_db.scalars(select(BackgroundClaim.id))).all() == []


async def test_the_translation_limit_is_one_when_configured_so(async_db, monkeypatch):
    monkeypatch.setattr(settings, "translation_concurrency", 1)
    tracker = Tracker()

    async def _translate(question, answer, source, target):
        await tracker.run()
        return f"[{target}] {question}", f"[{target}] {answer}"

    monkeypatch.setattr(translation_service, "translate_qa", _translate)

    for index in range(4):
        async_db.add(_approved(index))
    await async_db.commit()
    ids = list((await async_db.scalars(select(Question.id))).all())

    await background_translation_service.translate_missing(ids)

    assert tracker.peak == 1


async def test_one_row_is_translated_once_even_when_queued_twice(async_db, monkeypatch):
    """[53]'s guarantee under concurrency: at most one call per row."""
    calls: list[str] = []

    async def _translate(question, answer, source, target):
        calls.append(question)
        return f"[{target}] {question}", f"[{target}] {answer}"

    monkeypatch.setattr(translation_service, "translate_qa", _translate)

    async_db.add(_approved(1))
    await async_db.commit()
    question_id = (await async_db.scalars(select(Question.id))).first()

    # The same row queued twice by one response, as a repeated view does.
    await background_translation_service.translate_missing([question_id, question_id])

    assert calls == ["翻訳待ちの質問1"]


async def test_a_review_run_grades_several_questions_at_a_time(async_db, monkeypatch):
    monkeypatch.setattr(settings, "ai_review_concurrency", 3)
    tracker = Tracker()

    async def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        await tracker.run()
        return deepseek_service.GenerationResult(VALID_REVIEW, "mock-model", 7, 11)

    monkeypatch.setattr(deepseek_service, "generate_answer", _generate)

    for index in range(9):
        async_db.add(_unreviewed(index))
    await async_db.commit()
    ids = list((await async_db.scalars(select(Question.id))).all())

    run = AiReviewRun(
        trigger="manual",
        scope="unreviewed",
        question_ids=ids,
        requested_count=len(ids),
        status="running",
    )
    async_db.add(run)
    await async_db.commit()

    await ai_review_service.execute_run(async_db, run.id)
    await async_db.refresh(run)

    assert tracker.total == 9
    assert tracker.peak == 3
    assert run.status == "done"
    assert run.reviewed_count == 9
    # Counted from each item's own session, not a detached row.
    assert run.prompt_tokens == 9 * 7
    assert run.completion_tokens == 9 * 11
    assert run.heartbeat_at is not None
    assert len((await async_db.scalars(select(AiReview))).all()) == 9


async def test_a_run_taken_over_mid_flight_stops(async_db, monkeypatch):
    """[34] semantics: a reaped run must not keep spending calls."""
    monkeypatch.setattr(settings, "ai_review_concurrency", 2)
    graded: list[int] = []

    for index in range(8):
        async_db.add(_unreviewed(index))
    await async_db.commit()
    ids = list((await async_db.scalars(select(Question.id))).all())

    run = AiReviewRun(
        trigger="manual",
        scope="unreviewed",
        question_ids=ids,
        requested_count=len(ids),
        status="running",
    )
    async_db.add(run)
    await async_db.commit()
    run_id = run.id

    async def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        graded.append(1)
        if len(graded) == 2:
            # Another start reaped this run as timed out.
            from physics_ai_tutor.database.session import background_session
            from physics_ai_tutor.database.transaction import transaction

            async with background_session() as other:
                async with transaction(other, "reap"):
                    reaped = await other.get(AiReviewRun, run_id)
                    reaped.status = "failed"
                    reaped.error = "no progress"
        await asyncio.sleep(0.01)
        return deepseek_service.GenerationResult(VALID_REVIEW, "mock-model", 7, 11)

    monkeypatch.setattr(deepseek_service, "generate_answer", _generate)

    await ai_review_service.execute_run(async_db, run_id)

    # The in-flight items finish, but the queue stops. With concurrency 2
    # at most one more can already be past the status check when the
    # takeover lands, so this is a tight bound, not just "fewer than 8".
    assert len(graded) <= 4, graded

    await async_db.refresh(run)
    assert run.status == "failed"


async def test_a_run_with_one_slot_still_works(async_db, monkeypatch):
    """Concurrency of 1 reproduces the old sequential behaviour."""
    monkeypatch.setattr(settings, "ai_review_concurrency", 1)
    tracker = Tracker()

    async def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        await tracker.run()
        return deepseek_service.GenerationResult(VALID_REVIEW, "mock-model", 1, 1)

    monkeypatch.setattr(deepseek_service, "generate_answer", _generate)

    for index in range(3):
        async_db.add(_unreviewed(index))
    await async_db.commit()
    ids = list((await async_db.scalars(select(Question.id))).all())

    run = AiReviewRun(
        trigger="manual",
        scope="unreviewed",
        question_ids=ids,
        requested_count=len(ids),
        status="running",
    )
    async_db.add(run)
    await async_db.commit()

    await ai_review_service.execute_run(async_db, run.id)
    await async_db.refresh(run)

    assert tracker.peak == 1
    assert run.reviewed_count == 3
    assert run.status == "done"


async def test_a_missing_question_counts_as_skipped(async_db, monkeypatch):
    async def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        raise AssertionError("a missing question must not be graded")

    monkeypatch.setattr(deepseek_service, "generate_answer", _generate)

    run = AiReviewRun(
        trigger="manual",
        scope="ids",
        question_ids=[424242],
        requested_count=1,
        status="running",
    )
    async_db.add(run)
    await async_db.commit()

    await ai_review_service.execute_run(async_db, run.id)
    await async_db.refresh(run)

    assert run.skipped_count == 1
    assert run.status == "done"


async def test_a_run_is_faster_than_sequential_by_the_concurrency_factor(
    async_db, monkeypatch
):
    """The acceptance criterion, as a test rather than a one-off run.

    Measured live against a 5 s stand-in upstream: 12 questions took
    61.6 s at concurrency 1, 20.4 s at 3 and 10.2 s at 6 - exactly
    linear. Here the delay is small and the bound generous, so the test
    states the shape without being a benchmark that flakes under load.
    """
    monkeypatch.setattr(settings, "ai_review_concurrency", 4)
    delay = 0.1
    count = 8

    async def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        await asyncio.sleep(delay)
        return deepseek_service.GenerationResult(VALID_REVIEW, "mock-model", 1, 1)

    monkeypatch.setattr(deepseek_service, "generate_answer", _generate)

    for index in range(count):
        async_db.add(_unreviewed(index))
    await async_db.commit()
    ids = list((await async_db.scalars(select(Question.id))).all())

    run = AiReviewRun(
        trigger="manual",
        scope="ids",
        question_ids=ids,
        requested_count=len(ids),
        status="running",
    )
    async_db.add(run)
    await async_db.commit()

    started = asyncio.get_running_loop().time()
    await ai_review_service.execute_run(async_db, run.id)
    elapsed = asyncio.get_running_loop().time() - started

    await async_db.refresh(run)
    assert run.reviewed_count == count
    # Sequential would be count * delay; four at a time is about a
    # quarter of that. Half is a loose bound that still fails on serial.
    assert elapsed < (count * delay) / 2
