"""Background work is claimed in the database, not in the process ([75]).

These are the tests the in-process set could not pass: every claimer
below uses its own session, which is what a second uvicorn worker looks
like from the database's side.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database.session import async_background_session
from physics_ai_tutor.database.transaction import async_transaction
from physics_ai_tutor.models import BackgroundClaim, Question
from physics_ai_tutor.repositories import background_claim_repository as claims
from physics_ai_tutor.schemas.language import TextProvenance
from physics_ai_tutor.schemas.question import QuestionSource, QuestionStatus
from physics_ai_tutor.services import (
    background_translation_service,
    translation_service,
)

pytestmark = pytest.mark.anyio

KIND = claims.TRANSLATE_QUESTION
TIMEOUT = 15


def _approved(index: int) -> Question:
    return Question(
        question_ja=f"クレームのテスト質問{index}",
        answer_ja=f"回答{index}",
        ja_provenance=TextProvenance.ORIGINAL,
        original_language="ja",
        status=QuestionStatus.APPROVED,
        source=QuestionSource.MANUAL,
    )


async def _claim_in_own_session(key: int) -> bool:
    """Claim as a separate worker would: own session, own transaction."""
    async with async_background_session() as db:
        async with async_transaction(db, "test_claim"):
            return await claims.claim(db, KIND, key, TIMEOUT)


async def test_only_one_of_two_sessions_wins_a_claim(async_db):
    first = await _claim_in_own_session(4242)
    second = await _claim_in_own_session(4242)

    assert first is True
    assert second is False


async def test_many_simultaneous_claimers_produce_exactly_one_winner(async_db):
    """The real shape of the bug: several workers, one row, at once."""
    results = await asyncio.gather(*(_claim_in_own_session(777) for _ in range(8)))

    assert results.count(True) == 1
    assert results.count(False) == 7


async def test_a_released_claim_can_be_taken_again(async_db):
    assert await _claim_in_own_session(99) is True

    async with async_background_session() as db:
        async with async_transaction(db, "test_release"):
            await claims.release(db, KIND, 99)

    assert await _claim_in_own_session(99) is True


async def test_different_kinds_and_keys_do_not_collide(async_db):
    assert await _claim_in_own_session(1) is True

    async with async_background_session() as db:
        async with async_transaction(db, "test_claim"):
            # Same key, other kind of work.
            other_kind = await claims.claim(
                db, claims.TRANSLATE_CONCEPT_NAME, 1, TIMEOUT
            )
            # Same kind, other key.
            other_key = await claims.claim(db, KIND, 2, TIMEOUT)

    assert other_kind is True
    assert other_key is True


async def test_an_expired_claim_is_taken_over(async_db):
    """A worker that died mid-translation must not park the row ([75])."""
    assert await _claim_in_own_session(55) is True
    # Nobody released it: the worker crashed.
    assert await _claim_in_own_session(55) is False

    async with async_background_session() as db:
        async with async_transaction(db, "age_the_claim"):
            await db.execute(
                update(BackgroundClaim)
                .where(BackgroundClaim.kind == KIND, BackgroundClaim.key == 55)
                .values(claimed_at=datetime.now(UTC) - timedelta(minutes=TIMEOUT + 1))
            )

    assert await _claim_in_own_session(55) is True


async def test_a_fresh_claim_is_not_taken_over(async_db):
    """The timeout must not be so eager that live work is stolen."""
    assert await _claim_in_own_session(56) is True

    async with async_background_session() as db:
        async with async_transaction(db, "age_the_claim"):
            await db.execute(
                update(BackgroundClaim)
                .where(BackgroundClaim.kind == KIND, BackgroundClaim.key == 56)
                .values(claimed_at=datetime.now(UTC) - timedelta(minutes=TIMEOUT - 1))
            )

    assert await _claim_in_own_session(56) is False


async def test_a_row_another_worker_holds_is_not_translated(async_db, monkeypatch):
    """The point of the whole issue, end to end."""
    calls: list[str] = []

    async def _translate(question, answer, source, target):
        calls.append(question)
        return f"[{target}] {question}", f"[{target}] {answer}"

    monkeypatch.setattr(translation_service, "async_translate_qa", _translate)

    async_db.add(_approved(1))
    await async_db.commit()
    question_id = (await async_db.scalars(select(Question.id))).first()

    # Another worker took this row a moment ago and is still working.
    assert await _claim_in_own_session(question_id) is True

    await background_translation_service.translate_missing([question_id])

    assert calls == []
    row = await async_db.get(Question, question_id)
    await async_db.refresh(row)
    assert row.question_en is None
    # The other worker's claim is left alone, not released by the loser.
    async with async_background_session() as db:
        assert await claims.is_claimed(db, KIND, question_id) is True


async def test_a_translated_row_leaves_no_claim_behind(async_db, monkeypatch):
    async def _translate(question, answer, source, target):
        return f"[{target}] {question}", f"[{target}] {answer}"

    monkeypatch.setattr(translation_service, "async_translate_qa", _translate)

    async_db.add(_approved(2))
    await async_db.commit()
    question_id = (await async_db.scalars(select(Question.id))).first()

    await background_translation_service.translate_missing([question_id])

    row = await async_db.get(Question, question_id)
    await async_db.refresh(row)
    assert row.question_en is not None
    async with async_background_session() as db:
        assert await claims.is_claimed(db, KIND, question_id) is False


async def test_a_failing_translation_still_releases_its_claim(async_db, monkeypatch):
    """Otherwise one bad row would be untranslatable until the timeout."""

    async def _boom(question, answer, source, target):
        raise RuntimeError("translator down")

    monkeypatch.setattr(translation_service, "async_translate_qa", _boom)

    async_db.add(_approved(3))
    await async_db.commit()
    question_id = (await async_db.scalars(select(Question.id))).first()

    await background_translation_service.translate_missing([question_id])

    async with async_background_session() as db:
        assert await claims.is_claimed(db, KIND, question_id) is False


async def test_the_claim_timeout_comes_from_the_settings(async_db, monkeypatch):
    monkeypatch.setattr(settings, "background_claim_timeout_minutes", 1)

    assert await _claim_in_own_session(81) is True

    async with async_background_session() as db:
        async with async_transaction(db, "age_the_claim"):
            await db.execute(
                update(BackgroundClaim)
                .where(BackgroundClaim.kind == KIND, BackgroundClaim.key == 81)
                .values(claimed_at=datetime.now(UTC) - timedelta(minutes=2))
            )
        # Two minutes old is expired at a one-minute timeout.
        async with async_transaction(db, "test_claim"):
            assert (
                await claims.claim(
                    db, KIND, 81, settings.background_claim_timeout_minutes
                )
                is True
            )
