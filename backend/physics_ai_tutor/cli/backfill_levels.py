"""Backfill two-axis difficulty levels (and v4 concepts) for old questions.

Re-runs concept extraction for questions that have no difficulty rating
yet, which also refreshes their concepts under the current prompt - one
pass serves [39] and [40]. Restartable by construction: rated questions
are never selected again, so re-running continues where the last run
stopped. One DeepSeek call per question; respects the off-peak window
like review_pending ([26]) unless --force.
"""

import argparse
import sys

from physics_ai_tutor.cli.review_pending import (
    EXIT_FAILED,
    EXIT_OK,
    EXIT_OUTSIDE_WINDOW,
    _now,
    within_offpeak,
)
from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.models import Question
from physics_ai_tutor.services import question_service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=50, help="Maximum questions this run."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even outside the off-peak window (full price).",
    )
    return parser.parse_args()


def unrated_question_ids(db, limit: int) -> list[int]:
    """Oldest unrated APPROVED questions.

    Only APPROVED rows need the backfill: extraction (and with it the
    rating) already runs whenever a question becomes APPROVED, so
    UNREVIEWED rows are rated on approval and REJECTED ones never matter.
    """
    rows = (
        db.query(Question.id)
        .filter(
            Question.physics_level.is_(None),
            Question.math_level.is_(None),
            Question.status == "APPROVED",
        )
        .order_by(Question.id.asc())
        .limit(limit)
        .all()
    )

    return [question_id for (question_id,) in rows]


def main(limit: int = 50, force: bool = False) -> int:
    if not force and not within_offpeak(
        _now(), settings.ai_review_offpeak_start, settings.ai_review_offpeak_end
    ):
        print(
            "Refusing to start: outside the DeepSeek off-peak window "
            f"(UTC {settings.ai_review_offpeak_start}-"
            f"{settings.ai_review_offpeak_end}). "
            "Re-run with --force to pay the full tariff.",
            file=sys.stderr,
        )
        return EXIT_OUTSIDE_WINDOW

    db = SessionLocal()

    try:
        ids = unrated_question_ids(db, limit)
        if not ids:
            print("Every APPROVED question already has levels")
            return EXIT_OK

        results = question_service.reextract_concepts_for_questions(db, ids)
        succeeded = sum(1 for result in results if result.success)
        failed = len(results) - succeeded
        remaining = len(unrated_question_ids(db, limit=1))

        print(
            f"Rated {succeeded} questions ({failed} failed); "
            + ("more remain - re-run to continue" if remaining else "backfill done")
        )

        return EXIT_OK if failed == 0 else EXIT_FAILED
    finally:
        db.close()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.limit, args.force))
