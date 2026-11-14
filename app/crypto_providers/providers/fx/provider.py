"""
FX provider — implements BaseCryptoProvider on top of a pluggable
rate source.

Imports `app.crypto_market.market_data.interfaces` directly (the ONE
authorized cross-module import — the provider contract, not the
implementation). No import of any source module: duck typing, so
this file is importable regardless of which source is used.

Symbols filter behaviour
------------------------
`fetch_coins(symbols=...)` IGNORES the `symbols` argument. Reason:
FX rates are infrastructure, not per-coin data. The aggregator
needs them for every poll cycle regardless of which coins the user
has requested. Filtering them out by symbol would break FX
conversion in any future consumer that calls with a symbol filter.
The cost of returning the full set is trivial (typically 1–5 rows).

Cache
-----
Rates are cached for `cache_ttl` seconds (default 60). CoinGecko and
Nobitex poll every 10s; without caching, FX sources would be hit 6
times per minute per active session. 60s is well below the typical
change rate of central-bank-adjacent FX rates, so the cache is a
strict win.

If a source returns an empty dict (e.g., navasan stub), the provider
returns whatever the cache has (possibly stale). If the cache is
also empty, it returns []. The aggregator treats an empty FX rate
set as "no conversion available" — a valid state, not an error.

Error model
-----------
`fetch_coins` never raises. The provider catches source exceptions,
logs at WARNING, and returns the cached (or empty) result.
"""
import asyncio
import time
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.crypto_market.market_data.interfaces import (
    BaseCryptoProvider,
    CAP_COINS,
    Kline,
    ProviderCoin,
)


PROVIDER_NAME = "fx"
SUPPORTED_QUOTES = frozenset({"RLS"})
DEFAULT_CACHE_TTL = 60.0


class FxProvider(BaseCryptoProvider):
    """
    FX rate provider. See module docstring for symbols, cache, and
    error semantics.
    """

    def __init__(
        self,
        source,
        logger=None,
        cache_ttl: float = DEFAULT_CACHE_TTL,
    ):
        self._source = source
        self._logger = logger
        self._cache_ttl = float(cache_ttl)

        # Cache state
        self._cached_rates: Optional[dict[str, Decimal]] = None
        self._cache_timestamp: float = 0.0
        self._cache_lock = asyncio.Lock()

    # ==========================================================
    # Identity
    # ==========================================================
    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def capabilities(self) -> set[str]:
        return frozenset({CAP_COINS})

    @property
    def supported_quotes(self) -> set[str]:
        return SUPPORTED_QUOTES

    # ==========================================================
    # Lifecycle
    # ==========================================================
    async def start(self) -> None:
        try:
            await self._source.start()
        except Exception as exc:
            self._log(
                f"FX source start failed: {exc}", level="WARNING"
            )

    async def stop(self) -> None:
        try:
            await self._source.stop()
        except Exception as exc:
            self._log(
                f"FX source stop failed: {exc}", level="WARNING"
            )

    # ==========================================================
    # Fetch
    # ==========================================================
    async def fetch_coins(
        self, symbols: Optional[list[str]] = None
    ) -> list[ProviderCoin]:
        """
        Return FX rate rows (one per currency).

        `symbols` is IGNORED — see module docstring.

        Returns [] if the source is unavailable and no stale cache
        exists.
        """
        rates = await self._get_rates_cached()
        if not rates:
            return []

        now = datetime.utcnow()
        result: list[ProviderCoin] = []
        for currency, rate in rates.items():
            result.append(ProviderCoin(
                canonical=currency,
                provider=PROVIDER_NAME,
                symbol=currency.lower(),
                quote="RLS",
                price=rate,
                change_24h=None,
                volume_24h=None,
                high_24h=None,
                low_24h=None,
                name=None,
                icon_url=None,
                updated_at=now,
            ))
        return result

    async def fetch_klines(
        self,
        canonical: str,
        quote: str,
        interval: str,
        limit: int = 100,
    ) -> list[Kline]:
        """FX has no OHLC data. Returns []. CAP_KLINES not advertised."""
        return []

    # ==========================================================
    # Introspection
    # ==========================================================
    def info(self) -> dict:
        return {
            "name":             self.name,
            "capabilities":     sorted(self.capabilities),
            "supported_quotes": sorted(self.supported_quotes),
            "cache_ttl":        self._cache_ttl,
            "cached_rates":     (
                sorted(self._cached_rates.keys())
                if self._cached_rates else []
            ),
        }

    # ==========================================================
    # Cache
    # ==========================================================
    async def _get_rates_cached(self) -> dict[str, Decimal]:
        """
        Return rates from cache if fresh; otherwise fetch from source.

        On fetch error, returns stale cache (if any). Never raises.
        """
        now = time.monotonic()
        if (
            self._cached_rates is not None
            and (now - self._cache_timestamp) < self._cache_ttl
        ):
            return self._cached_rates

        async with self._cache_lock:
            # Double-check after acquiring lock — another coroutine
            # may have refreshed while we waited.
            now = time.monotonic()
            if (
                self._cached_rates is not None
                and (now - self._cache_timestamp) < self._cache_ttl
            ):
                return self._cached_rates

            try:
                fresh = await self._source.get_rates()
            except Exception as exc:
                self._log(
                    f"FX source raised: {exc}", level="WARNING"
                )
                fresh = None

            if fresh:
                self._cached_rates = dict(fresh)
                self._cache_timestamp = now
                self._log(
                    f"FX rates refreshed: "
                    f"{sorted(self._cached_rates.keys())}"
                )
                return self._cached_rates

            # Fetch failed or returned empty — keep stale cache
            return self._cached_rates or {}

    # ==========================================================
    # Internal
    # ==========================================================
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
            f"FxProvider(currencies="
            f"{sorted(self._cached_rates.keys()) if self._cached_rates else []}, "
            f"cache_ttl={self._cache_ttl}s)"
        )


__all__ = [
    "FxProvider",
    "PROVIDER_NAME",
    "SUPPORTED_QUOTES",
    "DEFAULT_CACHE_TTL",
]
