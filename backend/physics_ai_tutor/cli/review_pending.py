"""Run the AI reviewer over the backlog as a recorded run.

Runs regardless of AI_REVIEW_ENABLED: invoking the command is the intent.
Each question costs one DeepSeek call; the rolling 24h cap still applies.

The command refuses to start outside DeepSeek's discounted window
(AI_REVIEW_OFFPEAK_START/END, UTC) unless --force is given, so bulk runs
land on the cheap tariff. The nightly job ([26]) uses --scope both to
review the pending backlog first and stale verdicts after it.
"""

import argparse
import sys
from datetime import UTC, datetime, time

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.services import ai_review_service

# Exit codes: 0 = reviewed (or nothing to do), 1 = did not review when it
# should have, 2 = refused because the time is outside the off-peak window.
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_OUTSIDE_WINDOW = 2


def _now() -> datetime:
    """Seam for tests; the window check needs a controllable clock."""
    return datetime.now(UTC)


def _parse_clock(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def within_offpeak(now: datetime, start: str, end: str) -> bool:
    """True when `now` (UTC) falls inside the window; it may wrap midnight."""
    start_time = _parse_clock(start)
    end_time = _parse_clock(end)
    current = now.timetz().replace(tzinfo=None)

    if start_time <= end_time:
        return start_time <= current < end_time

    return current >= start_time or current < end_time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=20, help="Maximum questions per scope."
    )
    parser.add_argument(
        "--scope",
        choices=["pending", "stale", "both"],
        default="pending",
        help="pending = no AI review yet; stale = reviewed by an older "
        "prompt; both = pending first, then stale (the nightly job).",
    )
    parser.add_argument(
        "--trigger",
        choices=["cli", "scheduled"],
        default="cli",
        help="Recorded on the run; the nightly workflow passes 'scheduled'.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Start even outside the off-peak window (full price).",
    )
    return parser.parse_args()


def _count_eligible(db, scope: str) -> int:
    if scope == "pending":
        return ai_review_service.count_pending(db)
    return ai_review_service.count_stale(db)


def main(
    limit: int = 20,
    scope: str = "pending",
    trigger: str = "cli",
    force: bool = False,
) -> int:
    """Process exit code: 0 when the work finished, 1 when it did not.

    A scheduled run ([26]) is only as useful as its failure signal, so a
    run that ends 'failed' must not look like success.
    """
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

    scopes = ["pending", "stale"] if scope == "both" else [scope]
    db = SessionLocal()
    reviewed_something = False

    try:
        for current_scope in scopes:
            if _count_eligible(db, current_scope) == 0:
                print(f"No {current_scope} questions to review")
                continue

            try:
                run = ai_review_service.start_run(
                    db, scope=current_scope, trigger=trigger, limit=limit
                )
            except ai_review_service.RunInProgressError:
                print("An AI review run is already in progress", file=sys.stderr)
                return EXIT_FAILED
            except ai_review_service.DailyCapExhaustedError:
                print("The daily AI review budget is exhausted", file=sys.stderr)
                # Spending the whole budget on `pending` is a normal night;
                # spending none of it on anything is a silent outage.
                return EXIT_OK if reviewed_something else EXIT_FAILED

            finished = ai_review_service.execute_run(db, run.id)
            assert finished is not None
            run = finished
            print(
                f"Reviewed {run.reviewed_count} {current_scope} questions "
                f"({run.skipped_count} skipped, {run.failed_count} failed, "
                f"run #{run.id} {run.status})"
            )
            if run.status != "done":
                print(
                    f"Run #{run.id} ended {run.status}: {run.error}",
                    file=sys.stderr,
                )
                return EXIT_FAILED

            reviewed_something = True

        return EXIT_OK
    finally:
        db.close()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.limit, args.scope, args.trigger, args.force))
