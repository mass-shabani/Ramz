"""
client — HTTP client for CoinGecko's public /coins/markets API.

Only the public /coins/markets endpoint. No API key required for the
free tier (30 req/min). Authenticated endpoints and Pro-tier features
are out of scope.

Timeout tuning
--------------
CoinGecko /coins/markets with per_page=100 can take 3-5 seconds.
The client uses an internal httpx timeout of 7 seconds (below the
poller's per-provider fetch_timeout of 8s) so that a slow response
does not get cancelled by the poller mid-read. If CoinGecko is
slower than 7s, the client returns None before the poller times
out — the caller gets a clean "provider unavailable" signal instead
of a CancelledError.

User-Agent
----------
CoinGecko does not require a specific User-Agent, but identifying
ourselves is good practice for their infrastructure team. Same
convention as Nobitex: `TraderBot/ramz-1.0`.
"""
from typing import Optional

import httpx

from .rate_limiter import RateLimiter


# Endpoint
MARKETS_PATH = "/coins/markets"

# Client identity
USER_AGENT = "TraderBot/ramz-1.0"

# Default timeout, deliberately below the poller's fetch_timeout (8s)
DEFAULT_TIMEOUT = 7.0

# CoinGecko free tier max per_page is 250. We use 100 for latency
# reasons — see module docstring in the parent package and the
# discussion in TASK 78.6.
DEFAULT_PER_PAGE = 100


class CoinGeckoClient:
    """
    Async HTTP client for CoinGecko /coins/markets.

    Lifecycle:
        client = CoinGeckoClient(rate_limiter, logger=...)
        await client.start()
        markets = await client.get_markets()
        await client.stop()
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(
        self,
        rate_limiter: RateLimiter,
        timeout: float = DEFAULT_TIMEOUT,
        per_page: int = DEFAULT_PER_PAGE,
        logger=None,
    ):
        if per_page < 1 or per_page > 250:
            raise ValueError(
                f"per_page must be 1..250, got {per_page}"
            )
        self._rate_limiter = rate_limiter
        self._timeout = float(timeout)
        self._per_page = int(per_page)
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
        self._log("CoinGeckoClient started")

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
        self._log("CoinGeckoClient stopped")

    # ----------------------------------------------------------
    # Data
    # ----------------------------------------------------------
    async def get_markets(self) -> Optional[list]:
        """
        Fetch /coins/markets for top coins by market cap in USD.

        Returns:
            On success: list of coin dicts (CoinGecko schema).
            On any failure: None.
        """
        if self._client is None:
            self._log(
                "get_markets called before start(); returning None",
                level="ERROR",
            )
            return None

        if not await self._rate_limiter.acquire(timeout=self._timeout):
            self._log(
                "Rate limiter denied slot within timeout; "
                "skipping request",
                level="WARNING",
            )
            return None

        params = {
            "vs_currency":               "usd",
            "order":                     "market_cap_desc",
            "per_page":                  self._per_page,
            "page":                      1,
            "sparkline":                 "false",
            "price_change_percentage":   "24h",
        }

        try:
            response = await self._client.get(
                MARKETS_PATH, params=params
            )
        except httpx.TimeoutException as exc:
            self._log(
                f"get_markets timeout: {exc}", level="WARNING"
            )
            return None
        except httpx.RequestError as exc:
            self._log(
                f"get_markets request error: {exc}",
                level="WARNING",
            )
            return None
        except Exception as exc:
            self._log(
                f"get_markets unexpected error: {exc}",
                level="ERROR",
            )
            return None

        if response.status_code != 200:
            self._log(
                f"get_markets HTTP {response.status_code}",
                level="WARNING",
            )
            return None

        try:
            data = response.json()
        except Exception as exc:
            self._log(
                f"get_markets invalid JSON: {exc}",
                level="WARNING",
            )
            return None

        if not isinstance(data, list):
            self._log(
                "get_markets response is not a list",
                level="WARNING",
            )
            return None

        self._log(f"get_markets: {len(data)} coin(s) fetched")
        return data

    # ----------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------
    def is_started(self) -> bool:
        return self._client is not None

    def info(self) -> dict:
        return {
            "base_url":     self.BASE_URL,
            "timeout":      self._timeout,
            "per_page":     self._per_page,
            "user_agent":   USER_AGENT,
            "is_started":   self.is_started(),
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
            f"CoinGeckoClient(started={self.is_started()}, "
            f"per_page={self._per_page}, timeout={self._timeout}s)"
        )


__all__ = [
    "CoinGeckoClient",
    "MARKETS_PATH",
    "USER_AGENT",
    "DEFAULT_TIMEOUT",
    "DEFAULT_PER_PAGE",
]
