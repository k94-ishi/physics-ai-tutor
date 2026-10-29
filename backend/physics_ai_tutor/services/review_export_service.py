import hashlib
import hmac
import json
from collections.abc import Iterator
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.repositories import (
    question_concept_repository,
    question_review_repository,
)

# Reviews written before this date lack the correction diff ([07]), the
# reason code ([08]) and generation metadata ([09]); they are excluded from
# exports unless explicitly requested.
REVIEW_DATA_CUTOFF = date(2026, 10, 28)

# Fields in the order they appear on each JSONL line.
EXPORT_FIELDS = [
    "review_id",
    "question_id",
    "language",
    "source",
    "generation_model",
    "prompt_version",
    "generation_mode",
    "retrieved_question_ids",
    "concepts",
    "question_before",
    "answer_before",
    "question_after",
    "answer_after",
    "action",
    "reason",
    "comment",
    "reviewer_kind",
    "reviewer_hash",
    "policy_name",
    "reviewed_at",
]


def reviewer_hash(reviewer_id: int | None) -> str | None:
    """Stable pseudonym for a reviewer; no user id leaves the system.

    Keyed with the JWT secret, so the hash cannot be reversed from the
    export alone. Rotating the secret changes every hash, which only
    affects cross-export linkage, not correctness.
    """
    if reviewer_id is None:
        return None

    digest = hmac.new(
        settings.jwt_secret_key.encode(), str(reviewer_id).encode(), hashlib.sha256
    )

    return digest.hexdigest()[:16]


def default_since() -> datetime:
    return datetime.combine(REVIEW_DATA_CUTOFF, datetime.min.time(), tzinfo=UTC)


def iter_export_rows(
    db: Session,
    since: datetime | None,
) -> Iterator[dict]:
    """One dict per review, oldest first. `since=None` means everything."""
    rows = question_review_repository.list_with_questions_since(db, since)

    # Concept names per question in the language the review was done in.
    concepts_by_language: dict[str, dict[int, list[str]]] = {}
    for language in {review.language for review, _ in rows}:
        ids = [question.id for review, question in rows if review.language == language]
        concepts_by_language[language] = (
            question_concept_repository.get_concepts_for_questions(
                db, ids, language=language
            )
        )

    for review, question in rows:
        yield {
            "review_id": review.id,
            "question_id": question.id,
            "language": review.language,
            "source": question.source,
            "generation_model": question.generation_model,
            "prompt_version": question.prompt_version,
            "generation_mode": question.generation_mode,
            "retrieved_question_ids": list(question.retrieved_question_ids or []),
            "concepts": concepts_by_language[review.language].get(question.id, []),
            "question_before": review.before_question,
            "answer_before": review.before_answer,
            "question_after": review.after_question,
            "answer_after": review.after_answer,
            "action": review.action,
            "reason": review.reason,
            "comment": review.comment,
            "reviewer_kind": review.reviewer_kind,
            "reviewer_hash": reviewer_hash(review.reviewer_id),
            "policy_name": review.policy_name,
            "reviewed_at": review.created_at.isoformat(),
        }


def to_jsonl(rows: Iterator[dict]) -> Iterator[str]:
    for row in rows:
        yield json.dumps(row, ensure_ascii=False) + "\n"
