"""
client — HTTP client for Nobitex's public market API.

Only public endpoints. Authenticated endpoints (orders, wallet) are
out of scope for phase 2 — they arrive with the crypto_trading module.

Error model
-----------
Every method returns None on error and logs a WARNING (or DEBUG for
transient errors). Never raises to the caller. The poller treats None
as "this provider failed for this cycle" and continues with the
others; provider.py (TASK 78.5) does the same.

No internal retry
-----------------
Retries are the poller's responsibility (next cycle after `interval`
seconds). Adding in-client retries would risk exceeding the poller's
per-provider timeout (8s) and complicate rate-limit accounting. Simpler
is better here.

Rate limiting
-------------
The client requires a RateLimiter at construction. Every call to
`get_market_stats()` acquires a slot first. Timeout on acquire is
`self._timeout` — if the rate limiter cannot grant a slot in that
window, the call returns None (as if the API were unavailable).

User-Agent
----------
Nobitex asks clients to identify themselves with
`TraderBot/<name-version>`. We use `TraderBot/ramz-1.0`. This is
required by Nobitex's fair-use policy and helps their team contact
us if our traffic pattern becomes problematic.
"""
from typing import Optional

import httpx

from .rate_limiter import RateLimiter


# Endpoints
STATS_PATH = "/market/stats"

# Client identity
USER_AGENT = "TraderBot/ramz-1.0"
DEFAULT_TIMEOUT = 8.0


class NobitexClient:
    """
    Async HTTP client for Nobitex /market/stats.

    Lifecycle:
        client = NobitexClient(rate_limiter, logger=...)
        await client.start()   # creates httpx.AsyncClient
        stats = await client.get_market_stats()
        await client.stop()    # closes httpx.AsyncClient

    See module docstring for error and rate-limit contracts.
    """

    BASE_URL = "https://apiv2.nobitex.ir"

    def __init__(
        self,
        rate_limiter: RateLimiter,
        timeout: float = DEFAULT_TIMEOUT,
        logger=None,
    ):
        self._rate_limiter = rate_limiter
        self._timeout = float(timeout)
        self._logger = logger
        self._client: Optional[httpx.AsyncClient] = None

    # ----------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------
    async def start(self) -> None:
        """Create the underlying httpx.AsyncClient. Idempotent."""
        if self._client is not None:
            return
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self._timeout,
            headers={
                "User-Agent": USER_AGENT,
                "Accept":     "application/json",
            },
        )
        self._log("NobitexClient started")

    async def stop(self) -> None:
        """Close the underlying client. Idempotent."""
        if self._client is None:
            return
        try:
            await self._client.aclose()
        except Exception as exc:
            self._log(
                f"Error closing httpx client: {exc}", level="WARNING"
            )
        self._client = None
        self._log("NobitexClient stopped")

    # ----------------------------------------------------------
    # Data
    # ----------------------------------------------------------
    async def get_market_stats(self) -> Optional[dict]:
        """
        Fetch /market/stats.

        Returns:
            On success: dict of market_key → stats_dict, e.g.
                {"btc-rls": {"latest": "...", ...}, "btc-usdt": {...}, ...}
            On any failure: None.
        """
        if self._client is None:
            self._log(
                "get_market_stats called before start(); returning None",
                level="ERROR",
            )
            return None

        # Rate limit
        if not await self._rate_limiter.acquire(timeout=self._timeout):
            self._log(
                "Rate limiter denied slot within timeout; "
                "skipping request",
                level="WARNING",
            )
            return None

        # HTTP request
        try:
            response = await self._client.get(STATS_PATH)
        except httpx.TimeoutException as exc:
            self._log(
                f"get_market_stats timeout: {exc}", level="WARNING"
            )
            return None
        except httpx.RequestError as exc:
            self._log(
                f"get_market_stats request error: {exc}",
                level="WARNING",
            )
            return None
        except Exception as exc:
            self._log(
                f"get_market_stats unexpected error: {exc}",
                level="ERROR",
            )
            return None

        # HTTP status
        if response.status_code != 200:
            self._log(
                f"get_market_stats HTTP {response.status_code}",
                level="WARNING",
            )
            return None

        # JSON parse
        try:
            data = response.json()
        except Exception as exc:
            self._log(
                f"get_market_stats invalid JSON: {exc}",
                level="WARNING",
            )
            return None

        if not isinstance(data, dict):
            self._log(
                "get_market_stats response is not a dict",
                level="WARNING",
            )
            return None

        # Nobitex envelope: {"status": "ok", "stats": {...}}
        status = data.get("status")
        if status != "ok":
            self._log(
                f"get_market_stats API status={status!r}",
                level="WARNING",
            )
            return None

        stats = data.get("stats")
        if not isinstance(stats, dict):
            self._log(
                "get_market_stats missing or invalid 'stats' field",
                level="WARNING",
            )
            return None

        self._log(f"get_market_stats: {len(stats)} market(s) fetched")
        return stats

    # ----------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------
    def is_started(self) -> bool:
        """True if the underlying httpx client exists."""
        return self._client is not None

    def info(self) -> dict:
        """Serializable status summary."""
        return {
            "base_url":    self.BASE_URL,
            "timeout":     self._timeout,
            "user_agent":  USER_AGENT,
            "is_started":  self.is_started(),
            "rate_limiter": (
                self._rate_limiter.info()
                if self._rate_limiter else None
            ),
        }

    # ----------------------------------------------------------
    # Internal
    # ----------------------------------------------------------
    def _log(self, message: str, level: str = "INFO") -> None:
        if self._logger:
            try:
                self._logger.log(
                    message, level=level, tag="crypto_providers"
                )
            except Exception:
                pass

    def __repr__(self) -> str:
        return (
            f"NobitexClient(started={self.is_started()}, "
            f"timeout={self._timeout}s)"
        )


__all__ = ["NobitexClient", "STATS_PATH", "USER_AGENT", "DEFAULT_TIMEOUT"]
