import threading
import time
from collections import defaultdict, deque


class RateLimitExceeded(Exception):
    pass


class SlidingWindowRateLimiter:
    """In-process, in-memory sliding-window rate limiter.

    Not shared across multiple worker processes/instances - acceptable for
    the current single-process deployment, but a residual limitation if the
    backend is later scaled horizontally.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, dict[int, deque[float]]] = defaultdict(dict)

    def check(self, key: str, limits: list[tuple[int, int]]) -> None:
        """limits: [(max_requests, window_seconds), ...].

        Raises RateLimitExceeded if any window's limit would be exceeded by
        this request; otherwise records the hit in all windows.
        """
        now = time.monotonic()

        with self._lock:
            windows = self._hits[key]

            for max_requests, window_seconds in limits:
                timestamps = windows.setdefault(window_seconds, deque())
                cutoff = now - window_seconds

                while timestamps and timestamps[0] < cutoff:
                    timestamps.popleft()

                if len(timestamps) >= max_requests:
                    raise RateLimitExceeded(key)

            for _, window_seconds in limits:
                windows[window_seconds].append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


ai_ask_rate_limiter = SlidingWindowRateLimiter()
