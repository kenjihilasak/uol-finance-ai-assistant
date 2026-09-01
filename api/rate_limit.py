"""Small in-memory limiter for the single-replica portfolio deployment."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable


class FixedWindowRateLimiter:
    def __init__(
        self,
        maximum: int,
        *,
        window_seconds: int = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if maximum <= 0 or window_seconds <= 0:
            raise ValueError("Rate limit values must be positive")
        self.maximum = maximum
        self.window_seconds = window_seconds
        self._clock = clock
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            requests = self._requests[key]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= self.maximum:
                retry_after = max(1, int(requests[0] + self.window_seconds - now) + 1)
                return False, retry_after
            requests.append(now)
            return True, 0
