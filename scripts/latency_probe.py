#!/usr/bin/env python3
"""Measure endpoint latency against a local stack ([68]).

Fires N requests at one endpoint, K at a time, and prints p50/p95/max.
Use it to show the thread-pool starvation this track is about: run a
batch of cheap requests while slow generations are in flight and watch
the cheap ones get slower.

Refuses any non-local base URL by design: this sends real traffic, and
against production it would spend quota and pollute the data. There is
no flag to override that.

    python scripts/latency_probe.py --path /api/v1/health -n 50 -c 10
    python scripts/latency_probe.py --path /api/v1/questions -n 100 -c 40

`{n}` anywhere in `--body` is replaced by the request index, which keeps
each request distinct so a server-side cache cannot absorb the run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urlparse

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
DEFAULT_BASE_URL = "http://localhost:8000"


@dataclass
class Result:
    duration_ms: float
    status: int | None
    error: str | None = None


def check_local(base_url: str) -> None:
    """Exit unless the target is this machine."""
    host = urlparse(base_url).hostname
    if host not in LOCAL_HOSTS:
        sys.exit(
            f"Refusing to probe {host!r}: only {sorted(LOCAL_HOSTS)} are allowed. "
            "This script sends real traffic and must never hit production."
        )


def request_once(
    url: str, body: bytes | None, timeout: float, headers: dict[str, str] | None = None
) -> Result:
    """One blocking request; network errors become a Result, not a crash."""
    sent = {"Content-Type": "application/json"} if body else {}
    sent.update(headers or {})
    req = urllib.request.Request(url, data=body, headers=sent)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response.read()
            status = response.status
        error = None
    except urllib.error.HTTPError as exc:
        status, error = exc.code, None
    except Exception as exc:
        status, error = None, type(exc).__name__
    return Result((time.perf_counter() - start) * 1000, status, error)


async def run_batch(
    url: str,
    body: bytes | None,
    count: int,
    concurrency: int,
    timeout: float,
    headers: dict[str, str] | None = None,
) -> list[Result]:
    """Send `count` requests, at most `concurrency` in flight."""
    semaphore = asyncio.Semaphore(concurrency)
    loop = asyncio.get_running_loop()

    async def one(index: int, pool: ThreadPoolExecutor) -> Result:
        async with semaphore:
            # `{n}` in the body keeps each request distinct, so a server-side
            # cache cannot absorb a concurrency run ([68]).
            sent = body.replace(b"{n}", str(index).encode()) if body else None
            return await loop.run_in_executor(
                pool, request_once, url, sent, timeout, headers
            )

    # One thread per in-flight request: asyncio's default executor caps at
    # about 12, which would silently become the measurement's own limit.
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        return list(await asyncio.gather(*(one(i, pool) for i in range(count))))


def summarise(label: str, results: list[Result]) -> None:
    durations = sorted(result.duration_ms for result in results)
    statuses: dict[str, int] = {}
    for result in results:
        key = result.error or str(result.status)
        statuses[key] = statuses.get(key, 0) + 1

    # Nearest-rank, not interpolated: an interpolated p95 can land above
    # the slowest request actually observed, which reads as invented data.
    p95 = durations[min(len(durations) - 1, math.ceil(0.95 * len(durations)) - 1)]

    print(f"\n{label}: n={len(durations)}")
    print(f"  p50 {statistics.median(durations):8.1f} ms")
    print(f"  p95 {p95:8.1f} ms")
    print(f"  max {durations[-1]:8.1f} ms")
    print(f"  responses: {statuses}")


async def main_async(args: argparse.Namespace) -> None:
    url = args.base_url.rstrip("/") + args.path
    body = args.body.encode() if args.body else None
    headers = dict(item.split(":", 1) for item in args.header)

    if args.warmup:
        request_once(url, body, args.timeout, headers)

    started = time.perf_counter()
    results = await run_batch(
        url, body, args.n, args.concurrency, args.timeout, headers
    )
    wall = time.perf_counter() - started

    summarise(f"{args.path} (concurrency {args.concurrency})", results)
    print(f"  wall {wall:8.1f} s total")

    if args.json_out:
        payload = {
            "path": args.path,
            "n": args.n,
            "concurrency": args.concurrency,
            "wall_seconds": round(wall, 3),
            "durations_ms": [round(r.duration_ms, 2) for r in results],
        }
        print(json.dumps(payload))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--path", default="/api/v1/health")
    parser.add_argument("-n", type=int, default=20, help="total requests")
    parser.add_argument("-c", "--concurrency", type=int, default=1)
    parser.add_argument("--body", help="JSON body; makes the request a POST")
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        metavar="NAME:VALUE",
        help="extra header, repeatable (e.g. a session cookie)",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--warmup", action="store_true", help="one request first")
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    check_local(args.base_url)
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
