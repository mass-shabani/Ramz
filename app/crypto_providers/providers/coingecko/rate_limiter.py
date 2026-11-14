"""
rate_limiter — sliding-window rate limiter for CoinGecko.

This is a copy of the Nobitex rate limiter (see
providers/nobitex/rate_limiter.py) with different defaults. The
code is deliberately not shared: keeping each provider's rate
limiter independent makes it trivial to swap one provider out
without affecting the other, and the file is small enough that
duplication is cheaper than a shared abstraction.

Default for CoinGecko free tier: 30 requests per 60 seconds.

The provider itself issues at most ~1 request per poll cycle (every
10s), so 30/min is far above the actual usage. The limiter is here
as a safety net against future misuse (e.g. if a future task adds
on-demand calls per symbol).
"""
import asyncio
import time
from collections import deque
from typing import Optional


DEFAULT_MAX_REQUESTS = 30
DEFAULT_WINDOW_SECONDS = 60.0
DEFAULT_THROTTLE_LOG_INTERVAL = 30.0


class RateLimiter:
    """Sliding-window async rate limiter. See module docstring."""

    def __init__(
        self,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        logger=None,
        name: str = "coingecko",
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
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()
        self._last_throttle_log: float = 0.0

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        start = time.monotonic()
        while True:
            async with self._lock:
                now = time.monotonic()
                while self._timestamps and (
                    now - self._timestamps[0]
                ) > self._window:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._max:
                    self._timestamps.append(now)
                    return True
                oldest = self._timestamps[0]
                wait = self._window - (now - oldest) + 0.01
                self._maybe_log_throttle(len(self._timestamps))
            if timeout is not None:
                elapsed = time.monotonic() - start
                if elapsed + wait > timeout:
                    return False
            await asyncio.sleep(min(wait, 0.5))

    def current_usage(self) -> int:
        now = time.monotonic()
        while self._timestamps and (
            now - self._timestamps[0]
        ) > self._window:
            self._timestamps.popleft()
        return len(self._timestamps)

    def reset(self) -> None:
        self._timestamps.clear()
        self._last_throttle_log = 0.0

    def info(self) -> dict:
        return {
            "name":          self._name,
            "max_requests":  self._max,
            "window_secs":   self._window,
            "current_usage": self.current_usage(),
        }

    def _maybe_log_throttle(self, count: int) -> None:
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
