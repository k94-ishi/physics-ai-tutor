"""Per-stage timing logs for the latency baseline ([68]).

A slow request's total time says nothing about where it went. Wrap the
waiting parts in `stage("name")` and each one logs its own duration, so
the stage lines of one request add up to the middleware's total.
"""

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# The path being served, so a stage line can be tied to its request.
_current_path: ContextVar[str] = ContextVar("current_path", default="-")


class Stage:
    """Handle of a running stage; `note()` adds fields to its log line."""

    def __init__(self) -> None:
        self.fields: dict[str, object] = {}

    def note(self, **fields: object) -> None:
        self.fields.update(fields)


@contextmanager
def request_path(path: str) -> Iterator[None]:
    """Name the request that the stages inside belong to."""
    token = _current_path.set(path)
    try:
        yield
    finally:
        _current_path.reset(token)


@contextmanager
def stage(name: str, **fields: object) -> Iterator[Stage]:
    """Log how long the block took, whether it succeeded or raised.

    A failed call's duration is part of the latency too, so the line is
    written from a `finally` and the exception travels on untouched.
    """
    current = Stage()
    current.fields.update(fields)
    start = time.perf_counter()
    try:
        yield current
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        extra = "".join(f" {key}={value}" for key, value in current.fields.items())
        logger.info(
            "Stage finished: name=%s path=%s duration_ms=%.2f%s",
            name,
            _current_path.get(),
            duration_ms,
            extra,
        )
