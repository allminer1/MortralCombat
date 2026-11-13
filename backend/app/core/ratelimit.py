"""Sliding-window rate limit per client, in process memory.

The API runs as a single uvicorn process (spec Section 4), so no shared store is
needed. Holds client addresses and timestamps only, for at most one window.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._last_sweep = clock()

    def check(self, key: str) -> int:
        """Record a request. Returns 0 if allowed, else seconds until the next slot."""
        if self.limit <= 0:
            return 0
        now = self._clock()
        with self._lock:
            if now - self._last_sweep > self.window:
                self._sweep(now)
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, math.ceil(self.window - (now - hits[0])))
            hits.append(now)
            return 0

    def _sweep(self, now: float) -> None:
        """Forget clients with no request inside the window."""
        stale = [k for k, hits in self._hits.items() if not hits or now - hits[-1] >= self.window]
        for k in stale:
            del self._hits[k]
        self._last_sweep = now
