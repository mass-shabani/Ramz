"""
poller — conditional background loop that feeds the aggregator.

Responsibilities
----------------
Every `interval` seconds (default 10s), the poller:

    1. Checks the presence registry.
    2. If no UI session is active, SKIPS — no provider API calls.
    3. Otherwise, calls every registered provider that advertises
       CAP_COINS, concurrently (each with a per-provider timeout).
    4. Feeds the collected ProviderCoin rows into the aggregator.
    5. Stores the resulting CoinData snapshot for consumers.

Why a poll loop and not event-driven (WebSocket subscribe)?
-----------------------------------------------------------
Ramz is intentionally HTTP-first in phase 1: providers expose REST,
the browser opens a page, and the server pushes fresh data to the
page via the normal request/refresh cycle. Real-time push via
WebSocket is a phase-5 concern (see plan). The poll loop is the
simplest mechanism that satisfies "no traffic when nobody is
watching" (presence) while keeping providers untouched.

Dependency direction
--------------------
This class does NOT import ProviderRegistry, PresenceRegistry, or
Aggregator. It receives them as constructor arguments and calls
their public methods (duck typing). This keeps the poller:

    • testable with fakes (no need to build the real registries),
    • decoupled from internal changes in those modules.

The only imports are `CAP_COINS` (a constant) and `CoinData` (a DTO
returned by the aggregator). Both are stable public contracts.

Concurrency and locking
-----------------------
Two actors can trigger a fetch cycle:

    • The internal loop (every `interval` seconds).
    • An external caller via `refresh_now()` (see below).

To prevent double-fetches when both fire close together, all fetch
work is guarded by `_poll_lock` (an asyncio.Lock). A concurrent
`refresh_now()` that arrives while a cycle is in progress simply
waits — it does NOT trigger a second round. This is correct because
the data is already being refreshed.

`refresh_now()` also applies a soft debounce: if the last successful
refresh was less than `min_refresh_interval` ago, it returns False
without fetching. This prevents thundering-herd when many browsers
open a page in the same second and the route handler calls
`refresh_now()` per request. Use `force=True` for debugging or admin
actions that genuinely need a fresh cycle right now.
"""
import asyncio
import time
from typing import Optional

from .interfaces import CAP_COINS
from .types import CoinData


DEFAULT_INTERVAL = 10.0
DEFAULT_FETCH_TIMEOUT = 8.0
DEFAULT_MIN_REFRESH_INTERVAL = 3.0


class MarketPoller:
    """
    Conditional background loop that refreshes crypto_market data.

    Lifecycle
    ---------
    1. Instantiated by crypto_market (see market_service/api.py) with
       registry, aggregator, and presence references, plus optional
       logger and tuning parameters.
    2. `start()` is called from the owning module's start() (or from
       an ON_ALL_MODULES_STARTED hook) to spawn the loop.
    3. `stop()` is called during shutdown to cancel the loop cleanly.

    Snapshot access
    ---------------
    Consumers read the latest snapshot via `latest_coins()`. The list
    is replaced atomically on each successful cycle; a consumer that
    holds a reference from a previous call keeps seeing the old list
    (safe — CoinData objects are treated as immutable by convention).
    """

    def __init__(
        self,
        registry,
        aggregator,
        presence,
        logger=None,
        interval: float = DEFAULT_INTERVAL,
        fetch_timeout: float = DEFAULT_FETCH_TIMEOUT,
        min_refresh_interval: float = DEFAULT_MIN_REFRESH_INTERVAL,
    ):
        self._registry = registry
        self._aggregator = aggregator
        self._presence = presence
        self._logger = logger

        self._interval = float(interval)
        self._fetch_timeout = float(fetch_timeout)
        self._min_refresh_interval = float(min_refresh_interval)

        # State
        self._latest_coins: list[CoinData] = []
        self._last_updated: Optional[float] = None
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._poll_lock = asyncio.Lock()
        self._empty_providers_logged: bool = False

    # ----------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------
    async def start(self) -> None:
        """
        Spawn the background loop. Idempotent.

        Does not fetch immediately — the first fetch happens on the
        first loop iteration (after `interval` seconds) or when a UI
        session opens and the loop wakes up with presence > 0. Callers
        that want an immediate fetch at startup can call
        `refresh_now(force=True)` after `start()`.
        """
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        self._log(
            f"Poller started "
            f"(interval={self._interval}s, "
            f"fetch_timeout={self._fetch_timeout}s)"
        )

    async def stop(self) -> None:
        """
        Cancel the loop and wait for it to finish. Idempotent.
        """
        if not self._running and self._task is None:
            return

        self._running = False

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._log("Poller stopped")

    def is_running(self) -> bool:
        """True if the background loop task is currently active."""
        return (
            self._running
            and self._task is not None
            and not self._task.done()
        )

    # ----------------------------------------------------------
    # Snapshot access (sync)
    # ----------------------------------------------------------
    def latest_coins(self) -> list[CoinData]:
        """
        Return the most recent snapshot of aggregated coins.

        Returns the internal list directly (not a copy) because the
        poller replaces the reference on each cycle and never mutates
        the list in place. Consumers should treat the returned list
        and the CoinData objects in it as read-only. Sorting or
        filtering locally is fine — those operations do not affect
        the internal list.
        """
        return self._latest_coins

    def last_updated(self) -> Optional[float]:
        """
        Monotonic timestamp of the last successful fetch cycle, or
        None if no cycle has completed yet.
        """
        return self._last_updated

    def has_data(self) -> bool:
        """True if at least one successful cycle has populated data."""
        return self._last_updated is not None

    # ----------------------------------------------------------
    # Manual refresh
    # ----------------------------------------------------------
    async def refresh_now(self, force: bool = False) -> bool:
        """
        Force a fetch cycle.

        Unlike the background loop, this ignores presence — a caller
        who explicitly requests a refresh gets one even if no UI is
        active. Useful for admin debug and for route handlers that
        want to guarantee fresh data on first page open.

        Debounce:
            By default, if the last successful refresh was less than
            `min_refresh_interval` seconds ago, this returns False
            without fetching. Set `force=True` to bypass.

        Returns:
            True if a cycle ran (regardless of whether it produced
            data), False if debounced.
        """
        if not force and self._last_updated is not None:
            elapsed = time.monotonic() - self._last_updated
            if elapsed < self._min_refresh_interval:
                self._log(
                    f"refresh_now skipped (debounced; "
                    f"{elapsed:.1f}s < {self._min_refresh_interval}s)",
                    level="DEBUG",
                )
                return False

        try:
            await self._poll_cycle()
            return True
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._log(f"refresh_now failed: {exc}", level="ERROR")
            return False

    # ----------------------------------------------------------
    # Status
    # ----------------------------------------------------------
    def info(self) -> dict:
        """
        Serializable summary for logging and /status endpoints.

        Never returns provider instances or full coin data — only
        counts and timestamps.
        """
        return {
            "running":       self.is_running(),
            "interval":      self._interval,
            "fetch_timeout": self._fetch_timeout,
            "coin_count":    len(self._latest_coins),
            "has_data":      self._last_updated is not None,
            "last_updated":  self._last_updated,
        }

    # ----------------------------------------------------------
    # Loop
    # ----------------------------------------------------------
    async def _loop(self) -> None:
        """
        Background loop. Runs until `stop()` or cancellation.

        Sleeps `interval` before the first cycle (no immediate fetch
        at start — see start() docstring).
        """
        try:
            while self._running:
                # Sleep first, then poll. This avoids a burst of API
                # calls at startup if many module instances restart
                # together.
                try:
                    await asyncio.sleep(self._interval)
                except asyncio.CancelledError:
                    raise

                if not self._running:
                    break

                try:
                    await self._maybe_poll()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self._log(f"Poll cycle failed: {exc}", level="ERROR")
        except asyncio.CancelledError:
            # Expected on stop() — log at DEBUG and exit cleanly.
            self._log("Poller loop cancelled", level="DEBUG")
            raise

    async def _maybe_poll(self) -> None:
        """
        Poll only if at least one UI session is active.

        Presence is checked on every loop iteration. If no session is
        active, the cycle is a no-op — no provider API is called.
        """
        try:
            active = self._presence.active_count()
        except Exception as exc:
            self._log(
                f"Presence check failed ({exc}); skipping cycle",
                level="WARNING",
            )
            return

        if active == 0:
            return

        await self._poll_cycle()

    async def _poll_cycle(self) -> None:
        """
        One fetch-and-aggregate cycle.

        Wrapped in `_poll_lock` so that concurrent callers (background
        loop and refresh_now) do not race. A second caller arriving
        while the first is fetching waits, then returns immediately
        (the lock protects the work, not the state read at the end).
        """
        async with self._poll_lock:
            providers = self._registry.by_capability(CAP_COINS)

            if not providers:
                if not self._empty_providers_logged:
                    self._log(
                        "No providers registered for CAP_COINS; "
                        "poll cycle is a no-op. "
                        "(This warning is logged once.)",
                        level="WARNING",
                    )
                    self._empty_providers_logged = True
                return

            # Concurrent fetch from all providers, with per-provider timeout
            tasks = [
                self._fetch_from_provider(p) for p in providers
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            provider_coins = []
            for provider, result in zip(providers, results):
                if isinstance(result, BaseException):
                    self._log(
                        f"Provider '{self._safe_name(provider)}' failed: "
                        f"{result}",
                        level="WARNING",
                    )
                    continue
                if isinstance(result, list):
                    provider_coins.extend(result)

            if not provider_coins:
                self._log(
                    "Poll cycle produced no rows from any provider",
                    level="DEBUG",
                )
                return

            try:
                aggregated = self._aggregator.aggregate(provider_coins)
            except Exception as exc:
                self._log(
                    f"Aggregator raised: {exc}",
                    level="ERROR",
                )
                return

            # Atomic replacement — consumers with an old reference keep
            # seeing the old snapshot until their next call.
            self._latest_coins = aggregated
            self._last_updated = time.monotonic()

            self._log(
                f"Poll cycle complete: "
                f"{len(provider_coins)} rows → "
                f"{len(aggregated)} coins"
            )

    async def _fetch_from_provider(self, provider) -> list:
        """
        Fetch coins from one provider with a per-call timeout.

        Raises TimeoutError on timeout. Any other exception from the
        provider propagates to gather, which stores it as a result.
        The poller treats both as "provider failed for this cycle".
        """
        try:
            return await asyncio.wait_for(
                provider.fetch_coins(),
                timeout=self._fetch_timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"timeout after {self._fetch_timeout}s"
            )

    # ----------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------
    @staticmethod
    def _safe_name(provider) -> str:
        """
        Return provider.name without assuming the attribute exists.
        Used only for log messages when a provider misbehaves.
        """
        try:
            return getattr(provider, "name", None) or repr(provider)
        except Exception:
            return "<unknown>"

    def _log(self, message: str, level: str = "INFO") -> None:
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="crypto_market")
            except Exception:
                pass

    def __repr__(self) -> str:
        return (
            f"MarketPoller(running={self.is_running()}, "
            f"interval={self._interval}s, "
            f"coins={len(self._latest_coins)})"
        )


__all__ = [
    "MarketPoller",
    "DEFAULT_INTERVAL",
    "DEFAULT_FETCH_TIMEOUT",
    "DEFAULT_MIN_REFRESH_INTERVAL",
]
