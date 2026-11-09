"""Translate approved rows a student could not read, once, after the response ([53]).

Public responses leave out rows that lack the requested language; their
ids are queued here so the next view shows them. Each row costs at most
one DeepSeek call: only APPROVED rows are translated, a row already in
flight is skipped, and a translated row never reaches the queue again.
"""

import logging
import threading

from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.schemas.question import QuestionStatus
from physics_ai_tutor.services import question_service

logger = logging.getLogger(__name__)

_in_flight: set[int] = set()
_lock = threading.Lock()


def claim(question_ids: list[int]) -> list[int]:
    """Reserve ids not already being translated; returns the reserved ones."""
    with _lock:
        claimed = [qid for qid in dict.fromkeys(question_ids) if qid not in _in_flight]
        _in_flight.update(claimed)
    return claimed


def _release(question_id: int) -> None:
    with _lock:
        _in_flight.discard(question_id)


def translate_missing(question_ids: list[int]) -> None:
    """Background task body; opens its own session and never raises."""
    db = SessionLocal()
    try:
        for question_id in question_ids:
            try:
                question = db.get(Question, question_id)
                # Re-check: the row may have been unapproved since the request.
                if question is not None and question.status == QuestionStatus.APPROVED:
                    question_service.translate_missing_languages(db, question_id)
            except Exception:
                logger.warning(
                    "Background translation failed: question_id=%d",
                    question_id,
                    exc_info=True,
                )
                db.rollback()
            finally:
                _release(question_id)
    finally:
        db.close()
