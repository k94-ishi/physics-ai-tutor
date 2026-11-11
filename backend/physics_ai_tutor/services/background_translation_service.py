"""Translate approved rows a student could not read, once, after the response ([53]).

Public responses leave out rows that lack the requested language; their
ids are queued here so the next view shows them. Each row costs at most
one DeepSeek call: only APPROVED rows are translated, a row already in
flight is skipped, and a translated row never reaches the queue again.

Rows are translated a few at a time ([72]). Each concurrent item opens
its own session, because a SQLAlchemy session is not safe to share
between tasks running at once.

The in-flight sets below hold within **one process**. That is enough for
the single worker this runs on today; making the claim correct across
workers is [75], and the two mechanisms answer different questions - the
semaphore bounds one worker's request rate, a database claim bounds
duplication across all of them.
"""

import asyncio
import logging

from physics_ai_tutor.core import timing
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database.session import async_background_session
from physics_ai_tutor.database.transaction import async_transaction
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.schemas.question import QuestionStatus
from physics_ai_tutor.services import concept_service
from physics_ai_tutor.services.question_translation_service import (
    async_translate_missing_languages as translate_languages,
)

logger = logging.getLogger(__name__)

# Single-event-loop state: claim and release never await between the read
# and the write, so no lock is needed ([72] replaced the threading one).
_in_flight: set[int] = set()
_concepts_in_flight: set[int] = set()


def claim(question_ids: list[int]) -> list[int]:
    """Reserve ids not already being translated; returns the reserved ones."""
    claimed = [qid for qid in dict.fromkeys(question_ids) if qid not in _in_flight]
    _in_flight.update(claimed)
    return claimed


def release(question_id: int) -> None:
    """Drop a claim, whether the translation worked or not."""
    _in_flight.discard(question_id)


def release_concept(concept_id: int) -> None:
    """Drop a concept-name claim."""
    _concepts_in_flight.discard(concept_id)


def claim_concepts(concept_ids: list[int]) -> list[int]:
    """Reserve concept ids whose name is not already being translated."""
    claimed = [
        cid for cid in dict.fromkeys(concept_ids) if cid not in _concepts_in_flight
    ]
    _concepts_in_flight.update(claimed)
    return claimed


def _limiter() -> asyncio.Semaphore:
    return asyncio.Semaphore(max(1, settings.translation_concurrency))


async def translate_missing(question_ids: list[int]) -> None:
    """Background task body; never raises ([72])."""
    limiter = _limiter()

    async def one(question_id: int) -> None:
        async with limiter:
            try:
                async with async_background_session() as db:
                    async with async_transaction(db, "background_translate_check"):
                        question = await db.get(Question, question_id)
                        # The row may have been unapproved since the request.
                        approved = (
                            question is not None
                            and question.status == QuestionStatus.APPROVED
                        )

                    if approved:
                        await translate_languages(db, question_id)
            except Exception:
                logger.warning(
                    "Background translation failed: question_id=%d",
                    question_id,
                    exc_info=True,
                )
            finally:
                release(question_id)

    with timing.request_path("background:translate"):
        await asyncio.gather(*(one(qid) for qid in question_ids))


async def translate_concept_names(concept_ids: list[int]) -> None:
    """Background task body for missing concept names; never raises ([72])."""
    limiter = _limiter()

    async def one(concept_id: int) -> None:
        async with limiter:
            try:
                async with async_background_session() as db:
                    await concept_service.async_translate_missing_name(db, concept_id)
            except Exception:
                logger.warning(
                    "Concept name translation failed: concept_id=%d",
                    concept_id,
                    exc_info=True,
                )
            finally:
                release_concept(concept_id)

    with timing.request_path("background:translate_concept"):
        await asyncio.gather(*(one(cid) for cid in concept_ids))
