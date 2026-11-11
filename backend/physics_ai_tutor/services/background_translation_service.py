"""Translate approved rows a student could not read, once, after the response ([53]).

Public responses leave out rows that lack the requested language; their
ids are queued here so the next view shows them. Each row costs at most
one DeepSeek call: only APPROVED rows are translated, a row another
worker is already translating is skipped, and a translated row never
reaches the queue again.

Rows are translated a few at a time ([72]). Each concurrent item opens
its own session, because a SQLAlchemy session is not safe to share
between tasks running at once.

The skip is a **database claim** ([75]), not a set in this process. The
two limits answer different questions and both are needed: the semaphore
bounds how fast one worker calls DeepSeek, the claim stops two workers
doing the same row at all. The claim is taken inside the task rather
than by the caller, so it is held by whoever actually does the work.
"""

import asyncio
import logging

from physics_ai_tutor.core import timing
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database.session import async_background_session
from physics_ai_tutor.database.transaction import async_transaction
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.repositories import background_claim_repository
from physics_ai_tutor.schemas.question import QuestionStatus
from physics_ai_tutor.services import concept_service
from physics_ai_tutor.services.question_translation_service import (
    async_translate_missing_languages as translate_languages,
)

logger = logging.getLogger(__name__)


def _limiter() -> asyncio.Semaphore:
    return asyncio.Semaphore(max(1, settings.translation_concurrency))


async def _take(db, kind: str, key: int) -> bool:
    """Claim the work, committed so other workers can see it."""
    async with async_transaction(db, "claim_background_work"):
        return await background_claim_repository.claim(
            db, kind, key, settings.background_claim_timeout_minutes
        )


async def _give_back(db, kind: str, key: int) -> None:
    """Release the claim; a failure here only delays the next attempt."""
    try:
        async with async_transaction(db, "release_background_work"):
            await background_claim_repository.release(db, kind, key)
    except Exception:
        # The claim expires on its own, so this must never mask the work's
        # own outcome.
        logger.warning(
            "Releasing background claim failed: kind=%s key=%d",
            kind,
            key,
            exc_info=True,
        )


async def translate_missing(question_ids: list[int]) -> None:
    """Background task body; never raises ([72], [75])."""
    limiter = _limiter()
    kind = background_claim_repository.TRANSLATE_QUESTION

    async def one(question_id: int) -> None:
        async with limiter:
            async with async_background_session() as db:
                if not await _take(db, kind, question_id):
                    logger.info(
                        "Background translation skipped: question_id=%d reason=claimed",
                        question_id,
                    )
                    return

                try:
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
                    await _give_back(db, kind, question_id)

    with timing.request_path("background:translate"):
        await asyncio.gather(*(one(qid) for qid in dict.fromkeys(question_ids)))


async def translate_concept_names(concept_ids: list[int]) -> None:
    """Background task body for missing concept names; never raises."""
    limiter = _limiter()
    kind = background_claim_repository.TRANSLATE_CONCEPT_NAME

    async def one(concept_id: int) -> None:
        async with limiter:
            async with async_background_session() as db:
                if not await _take(db, kind, concept_id):
                    logger.info(
                        "Concept name translation skipped: concept_id=%d "
                        "reason=claimed",
                        concept_id,
                    )
                    return

                try:
                    await concept_service.async_translate_missing_name(db, concept_id)
                except Exception:
                    logger.warning(
                        "Concept name translation failed: concept_id=%d",
                        concept_id,
                        exc_info=True,
                    )
                finally:
                    await _give_back(db, kind, concept_id)

    with timing.request_path("background:translate_concept"):
        await asyncio.gather(*(one(cid) for cid in dict.fromkeys(concept_ids)))
