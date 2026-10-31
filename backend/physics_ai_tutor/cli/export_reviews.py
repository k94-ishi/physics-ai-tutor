import argparse
import sys
from datetime import UTC, date, datetime

from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.services import review_export_service


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export the human review history as JSONL (one review per line). "
            "Rows before the 2026-10-28 data cutoff are skipped unless --all."
        ),
    )
    parser.add_argument(
        "--since",
        type=date.fromisoformat,
        default=None,
        help="Inclusive start date (YYYY-MM-DD). Defaults to the data cutoff.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include every review, ignoring the cutoff and --since.",
    )
    parser.add_argument(
        "--out",
        default="-",
        help="Output file path; '-' (default) writes to stdout.",
    )
    return parser.parse_args(argv)


def resolve_since(since: date | None, include_all: bool) -> datetime | None:
    if include_all:
        return None
    if since is None:
        return review_export_service.default_since()
    return datetime.combine(since, datetime.min.time(), tzinfo=UTC)


def main(since: date | None = None, include_all: bool = False, out: str = "-") -> int:
    db = SessionLocal()
    count = 0

    try:
        start = resolve_since(since, include_all)
        lines = review_export_service.to_jsonl(
            review_export_service.iter_export_rows(db, start)
        )
        handle = sys.stdout if out == "-" else open(out, "w", encoding="utf-8")
        try:
            for line in lines:
                handle.write(line)
                count += 1
        finally:
            if handle is not sys.stdout:
                handle.close()
    finally:
        db.close()

    print(f"Exported {count} reviews", file=sys.stderr)
    return count


if __name__ == "__main__":
    args = parse_args()
    main(args.since, args.all, args.out)
