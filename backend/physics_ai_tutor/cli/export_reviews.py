import argparse
import asyncio
import sys
from datetime import UTC, date, datetime
from typing import TextIO

from physics_ai_tutor.database.database import AsyncSessionLocal
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


async def _write_rows(start: datetime | None, handle: TextIO) -> int:
    """Async since [96]; the CLI opens its own session."""
    async with AsyncSessionLocal() as db:
        rows = [row async for row in review_export_service.iter_export_rows(db, start)]

    count = 0
    for line in review_export_service.to_jsonl(rows):
        handle.write(line)
        count += 1

    return count


def main(since: date | None = None, include_all: bool = False, out: str = "-") -> int:
    start = resolve_since(since, include_all)
    handle = sys.stdout if out == "-" else open(out, "w", encoding="utf-8")
    try:
        count = asyncio.run(_write_rows(start, handle))
    finally:
        if handle is not sys.stdout:
            handle.close()

    print(f"Exported {count} reviews", file=sys.stderr)
    return count


if __name__ == "__main__":
    args = parse_args()
    main(args.since, args.all, args.out)
