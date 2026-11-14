"""
rate_limiter — sliding-window rate limiter for Nobitex API calls.

Implements a per-instance sliding window over timestamps. Each call to
`acquire()` records a timestamp; if the window is saturated, the
caller sleeps until the oldest timestamp expires.

Design notes
------------
    • Sliding window (not token bucket) — simpler to reason about,
      matches API rate limits expressed as "N requests per T seconds".
    • The internal `_timestamps` deque grows at most to `max_requests`,
      so memory is bounded.
    • `acquire()` releases the lock during sleep, allowing concurrent
      waiters to interleave. Under normal operation (well below limit)
      no waiting occurs.
    • Throttle log is rate-limited to one warning per 30s to avoid
      log spam if the caller hammers the limiter.

Defaults for Nobitex:
    • /market/stats   — 20 req/min (per Nobitex documentation)
    • /v3/orderbook   — 300 req/min
    • /v2/depth       — 300 req/min
    • /v2/trades      — 60 req/min

This task only implements the `/market/stats` limiter (20/min). Later
tasks may create additional limiters for other endpoints.
"""
import asyncio
import time
from collections import deque
from typing import Optional


DEFAULT_MAX_REQUESTS = 20
DEFAULT_WINDOW_SECONDS = 60.0
DEFAULT_THROTTLE_LOG_INTERVAL = 30.0


class RateLimiter:
    """
    Sliding-window async rate limiter.

    See module docstring for design notes.
    """

    def __init__(
        self,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        logger=None,
        name: str = "nobitex",
    ):
        if max_requests <= 0:
            raise ValueError(
                f"max_requests must be positive, got {max_requests}"
            )
        if window_seconds <= 0:
            raise ValueError(
                f"window_seconds must be positive, got {window_seconds}"
            )
        self._max = int(max_requests)
        self._window = float(window_seconds)
        self._logger = logger
        self._name = name

        # Deque of monotonic timestamps, oldest-first.
        self._timestamps: deque[float] = deque()
        # Serializes acquisition attempts so two callers cannot both
        # see "one slot left" and both grab it.
        self._lock = asyncio.Lock()

        # Throttle logging (rate-limit the rate-limit warnings themselves)
        self._last_throttle_log: float = 0.0

    # ----------------------------------------------------------
    # Public
    # ----------------------------------------------------------
    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until a slot is available, then record a request.

        Args:
            timeout: Maximum seconds to wait. If None, waits
                indefinitely (bounded only by loop lifetime).

        Returns:
            True if a slot was acquired (a request should proceed).
            False if the timeout elapsed before a slot was available.
        """
        start = time.monotonic()

        while True:
            # Critical section: evict old, check capacity, reserve slot.
            async with self._lock:
                now = time.monotonic()
                # Drop timestamps older than window.
                while self._timestamps and (
                    now - self._timestamps[0]
                ) > self._window:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._max:
                    self._timestamps.append(now)
                    return True

                # At limit: compute how long until the oldest expires.
                oldest = self._timestamps[0]
                wait = self._window - (now - oldest) + 0.01

                self._maybe_log_throttle(len(self._timestamps))

            # Release lock during sleep so other waiters can re-check
            # (avoids serializing all waiters on one lock).
            if timeout is not None:
                elapsed = time.monotonic() - start
                if elapsed + wait > timeout:
                    return False

            # Cap sleep chunk so periodic re-checks happen even if the
            # wall clock drifts; 0.5s granularity is plenty.
            await asyncio.sleep(min(wait, 0.5))

    def current_usage(self) -> int:
        """Number of slots used in the current window."""
        now = time.monotonic()
        # Approximate: drops expired on read without lock. Fine for
        # logging; the authoritative count is inside acquire().
        while self._timestamps and (
            now - self._timestamps[0]
        ) > self._window:
            self._timestamps.popleft()
        return len(self._timestamps)

    def reset(self) -> None:
        """Clear all timestamps. Used in tests / hot-reload."""
        self._timestamps.clear()
        self._last_throttle_log = 0.0

    def info(self) -> dict:
        """Serializable summary for logging."""
        return {
            "name":          self._name,
            "max_requests":  self._max,
            "window_secs":   self._window,
            "current_usage": self.current_usage(),
        }

    # ----------------------------------------------------------
    # Internal
    # ----------------------------------------------------------
    def _maybe_log_throttle(self, count: int) -> None:
        """Log at most once per THROTTLE_LOG_INTERVAL."""
        now = time.monotonic()
        if now - self._last_throttle_log < DEFAULT_THROTTLE_LOG_INTERVAL:
            return
        self._last_throttle_log = now
        if self._logger:
            try:
                self._logger.log(
                    f"Rate limit approaching for '{self._name}' "
                    f"({count}/{self._max} in {self._window:.0f}s)",
                    level="WARNING", tag="crypto_providers",
                )
            except Exception:
                pass

    def __repr__(self) -> str:
        return (
            f"RateLimiter(name={self._name!r}, "
            f"usage={len(self._timestamps)}/{self._max} "
            f"in {self._window:.0f}s)"
        )


__all__ = [
    "RateLimiter",
    "DEFAULT_MAX_REQUESTS",
    "DEFAULT_WINDOW_SECONDS",
]
