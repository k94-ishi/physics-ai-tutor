"""Translate approved rows a student could not read, once, after the response ([53]).

Public responses leave out rows that lack the requested language; their
ids are queued here so the next view shows them. Each row costs at most
one DeepSeek call: only APPROVED rows are translated, a row already in
flight is skipped, and a translated row never reaches the queue again.
"""

import logging
import threading

from physics_ai_tutor.database.session import background_session
from physics_ai_tutor.database.transaction import transaction
from physics_ai_tutor.models.question import Question
from physics_ai_tutor.schemas.question import QuestionStatus
from physics_ai_tutor.services import concept_service, question_translation_service

logger = logging.getLogger(__name__)

_in_flight: set[int] = set()
_concepts_in_flight: set[int] = set()
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
    with background_session() as db:
        for question_id in question_ids:
            try:
                with transaction(db, "background_translate"):
                    question = db.get(Question, question_id)
                    # Re-check: the row may have been unapproved since the request.
                    if (
                        question is not None
                        and question.status == QuestionStatus.APPROVED
                    ):
                        question_translation_service.translate_missing_languages(
                            db, question_id
                        )
            except Exception:
                logger.warning(
                    "Background translation failed: question_id=%d",
                    question_id,
                    exc_info=True,
                )
            finally:
                _release(question_id)


def claim_concepts(concept_ids: list[int]) -> list[int]:
    """Reserve concept ids whose name is not already being translated."""
    with _lock:
        claimed = [
            cid for cid in dict.fromkeys(concept_ids) if cid not in _concepts_in_flight
        ]
        _concepts_in_flight.update(claimed)
    return claimed


def translate_concept_names(concept_ids: list[int]) -> None:
    """Background task body for missing concept names; never raises."""
    with background_session() as db:
        for concept_id in concept_ids:
            try:
                with transaction(db, "background_translate_concept"):
                    concept_service.translate_missing_name(db, concept_id)
            except Exception:
                logger.warning(
                    "Concept name translation failed: concept_id=%d",
                    concept_id,
                    exc_info=True,
                )
            finally:
                with _lock:
                    _concepts_in_flight.discard(concept_id)
