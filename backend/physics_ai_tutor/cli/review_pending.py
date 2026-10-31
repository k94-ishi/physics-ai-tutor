"""Run the AI reviewer over the backlog as a recorded run.

Runs regardless of AI_REVIEW_ENABLED: invoking the command is the intent.
Each question costs one DeepSeek call; the rolling 24h cap still applies.
"""

import argparse
import sys

from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.services import ai_review_service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=20, help="Maximum questions to review."
    )
    parser.add_argument(
        "--scope",
        choices=["pending", "stale"],
        default="pending",
        help="pending = no AI review yet; stale = reviewed by an older prompt.",
    )
    return parser.parse_args()


def main(limit: int = 20, scope: str = "pending") -> int:
    """Process exit code: 0 when the run finished, 1 when it did not.

    A scheduled run ([26]) is only as useful as its failure signal, so a
    run that ends 'failed' must not look like success.
    """
    db = SessionLocal()

    try:
        try:
            run = ai_review_service.start_run(
                db, scope=scope, trigger="cli", limit=limit
            )
        except ai_review_service.RunInProgressError:
            print("An AI review run is already in progress", file=sys.stderr)
            return 1
        except ai_review_service.DailyCapExhaustedError:
            print("The daily AI review budget is exhausted", file=sys.stderr)
            return 1

        finished = ai_review_service.execute_run(db, run.id)
        assert finished is not None
        run = finished
        print(
            f"Reviewed {run.reviewed_count} questions "
            f"({run.skipped_count} skipped, {run.failed_count} failed, "
            f"run #{run.id} {run.status})"
        )
        if run.status != "done":
            print(f"Run #{run.id} ended {run.status}: {run.error}", file=sys.stderr)
            return 1

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.limit, args.scope))
