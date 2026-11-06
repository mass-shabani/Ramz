"""
api — public service API of the crypto_market module.

`CryptoMarketService` is the single entry point that consuming modules
(`crypto_coins`, `crypto_charts`, future `crypto_trading`, `crypto_analysis`)
use to read crypto market data.

Design
------
The service is a thin facade. It does NOT implement business logic;
it delegates to:

    • `ProviderRegistry`      — provider lookup by capability/quote
    • `PresenceRegistry`      — active UI sessions
    • `Aggregator`            — merge logic (used indirectly via poller)
    • `MarketPoller`          — background fetch + cached snapshot

This keeps the service easy to test and easy to reason about: every
public method either reads a cached value, delegates to a provider,
or triggers an explicit refresh.

Data freshness
--------------
`get_coins()` / `get_coin()` read from the poller's in-memory snapshot.
The snapshot is refreshed by the background poller whenever at least
one UI session is active (see poller.py). Route handlers that want to
guarantee fresh data on first page open should call `refresh_now()`
before reading; `refresh_now()` has a built-in debounce (3s default).

`get_klines()` / `get_orderbook()` bypass the poller and call the
provider directly. Klines and orderbooks are typically large, are
fetched on-demand (when a chart opens), and are not pre-polled. A
future version may add a short-TTL cache; for now, each call hits the
provider. Providers are expected to enforce their own rate limits.

No FX rate helper
-----------------
A direct `get_fx_rate(from_ccy, to_ccy)` method is intentionally NOT
provided here. Two reasons:

    1. `reference_prices` in each `CoinData` already contains the
       FX-filled values (RLS, USD, USDT) for every coin. Consumers
       that need a rate can derive it from any coin.
    2. FX rates change slowly. A dedicated method would need its own
       cache to be useful, which adds complexity for a feature no
       current consumer needs.

If a future consumer genuinely needs raw FX, add it then — with a
cache — in a dedicated task.
"""
from typing import Optional

from ..market_data.interfaces import (
    CAP_KLINES,
    CAP_ORDERBOOK,
    Kline,
    Orderbook,
)
from ..market_data.types import CoinData


class CryptoMarketService:
    """
    Public API for crypto market data.

    See module docstring for the overall contract and design rationale.
    """

    def __init__(
        self,
        registry,
        presence,
        aggregator,
        poller,
        logger=None,
    ):
        self._registry = registry
        self._presence = presence
        self._aggregator = aggregator
        self._poller = poller
        self._logger = logger

    # ==========================================================
    # Data queries (from cached snapshot)
    # ==========================================================
    async def get_coins(
        self, canonicals: Optional[list[str]] = None
    ) -> list[CoinData]:
        """
        Return the current aggregated CoinData snapshot.

        The snapshot is the poller's most recent successful cycle.
        Between cycles it may be slightly stale (up to `interval`
        seconds). Call `refresh_now()` first if freshness matters.

        Args:
            canonicals: Optional list of uppercase canonical symbols
                to filter by (e.g. ["BTC", "ETH"]). None returns all.

        Returns:
            List of CoinData. Empty if no cycle has completed yet.
        """
        coins = self._poller.latest_coins()

        if not canonicals:
            return coins

        wanted = {c.upper() for c in canonicals if c}
        if not wanted:
            return coins

        return [c for c in coins if c.canonical in wanted]

    async def get_coin(
        self, canonical: str
    ) -> Optional[CoinData]:
        """
        Return the CoinData for a single canonical, or None.

        Linear scan of the snapshot. Fine for the current dataset size
        (hundreds of coins); if this ever becomes hot, add an index in
        the poller. Kept simple for now.
        """
        if not canonical:
            return None
        canonical = canonical.upper()
        for coin in self._poller.latest_coins():
            if coin.canonical == canonical:
                return coin
        return None

    # ==========================================================
    # On-demand fetches (bypass poller)
    # ==========================================================
    async def get_klines(
        self,
        canonical: str,
        quote: str,
        interval: str,
        limit: int = 100,
    ) -> list[Kline]:
        """
        Fetch OHLCV candles from the first capable provider.

        Providers are tried in registration order. A provider is
        skipped if it does not advertise CAP_KLINES or does not
        support `quote`. The first provider that returns a non-empty
        list wins; if all fail, returns [].

        Args:
            canonical: Uppercase canonical symbol.
            quote:     Quote currency (e.g. "USDT").
            interval:  Provider-specific interval string
                       (convention: "5m", "15m", "1h", "4h", "1d").
            limit:     Max candles, oldest-first.
        """
        if not canonical or not quote or not interval:
            return []
        canonical = canonical.upper()

        providers = self._registry.by_capability(CAP_KLINES)
        for provider in providers:
            if quote not in provider.supported_quotes:
                continue
            try:
                klines = await provider.fetch_klines(
                    canonical, quote, interval, limit
                )
                if klines:
                    self._log(
                        f"get_klines({canonical}/{quote}, {interval}): "
                        f"served by '{provider.name}' "
                        f"({len(klines)} candles)"
                    )
                    return klines
            except Exception as exc:
                self._log(
                    f"Provider '{provider.name}' fetch_klines failed: {exc}",
                    level="WARNING",
                )

        self._log(
            f"get_klines({canonical}/{quote}, {interval}): "
            f"no provider succeeded",
            level="DEBUG",
        )
        return []

    async def get_orderbook(
        self,
        canonical: str,
        quote: str,
        depth: int = 10,
    ) -> Optional[Orderbook]:
        """
        Fetch the top-of-book snapshot from the first capable provider.

        Same selection strategy as `get_klines`. Returns None if no
        provider succeeds.
        """
        if not canonical or not quote:
            return None
        canonical = canonical.upper()

        providers = self._registry.by_capability(CAP_ORDERBOOK)
        for provider in providers:
            if quote not in provider.supported_quotes:
                continue
            try:
                ob = await provider.fetch_orderbook(
                    canonical, quote, depth
                )
                if ob is not None:
                    self._log(
                        f"get_orderbook({canonical}/{quote}): "
                        f"served by '{provider.name}'"
                    )
                    return ob
            except Exception as exc:
                self._log(
                    f"Provider '{provider.name}' fetch_orderbook failed: "
                    f"{exc}",
                    level="WARNING",
                )

        return None

    # ==========================================================
    # Presence
    # ==========================================================
    def heartbeat(
        self, session_id: str, kinds: Optional[list[str]] = None
    ) -> None:
        """
        Record a UI heartbeat. See PresenceRegistry.heartbeat().

        Called by the presence routes (TASK 77.11). No side effect on
        the poller — if the caller wants to force a fetch, they must
        also call `refresh_now()`.
        """
        self._presence.heartbeat(session_id, kinds)

    def leave(
        self, session_id: str, kinds: Optional[list[str]] = None
    ) -> None:
        """Record a UI leave. See PresenceRegistry.leave()."""
        self._presence.leave(session_id, kinds)

    def has_active_viewers(self) -> bool:
        """True if at least one UI session has an unexpired heartbeat."""
        return self._presence.active_count() > 0

    def active_viewer_count(self) -> int:
        """Number of active UI sessions (after pruning expired)."""
        return self._presence.active_count()

    # ==========================================================
    # Refresh
    # ==========================================================
    async def refresh_now(self, force: bool = False) -> bool:
        """
        Trigger an immediate fetch cycle via the poller.

        Returns True if a cycle ran, False if debounced (see
        MarketPoller.refresh_now). Callers that genuinely need fresh
        data on first page load should use `force=False` — the
        debounce protects against thundering herd when many browsers
        open a page in the same second.
        """
        return await self._poller.refresh_now(force=force)

    # ==========================================================
    # Status
    # ==========================================================
    def has_data(self) -> bool:
        """True if at least one poll cycle has completed."""
        return self._poller.has_data()

    def info(self) -> dict:
        """
        Serializable status summary for logging and /status endpoints.

        Never returns provider instances or full coin data — only
        counts, timestamps, and capability lists.
        """
        return {
            "providers": self._registry.info(),
            "poller":    self._poller.info(),
            "presence":  self._presence.info(),
        }

    # ==========================================================
    # Internal
    # ==========================================================
    def _log(self, message: str, level: str = "INFO") -> None:
        if self._logger:
            try:
                self._logger.log(
                    message, level=level, tag="crypto_market"
                )
            except Exception:
                pass

    def __repr__(self) -> str:
        return (
            f"CryptoMarketService("
            f"providers={self._registry.count()}, "
            f"coins={len(self._poller.latest_coins())})"
        )


__all__ = ["CryptoMarketService"]
