"""
services — CoinsService (public API of crypto_coins module).

Thin wrapper over `crypto_market_service`. Reasons to wrap rather than
have routes call `crypto_market_service` directly:

    1. Future-proofing. When crypto_coins needs to add its own logic
       (favorites decoration, display-currency conversion, user-pref
       filtering), the routes should not know about that. The service
       is where those decisions live.
    2. Access control stays in routes. CoinsService has no notion of
       users or grants — it just serves data. Routes do the grant
       check, then call the service.

In this task (79.1), CoinsService is a pure passthrough. TASK 79.2
adds favorite decoration. TASK 79.3 adds display-currency helpers.

Design constraints
------------------
    • Methods are async (crypto_market_service is async).
    • Returns raw `CoinData` dataclasses (not dicts). Serialization is
      routes' responsibility — the service does not know about JSON
      or Jinja; it serves domain objects.
    • No caching here. crypto_market_service owns the snapshot.
"""
from typing import Optional

from app.crypto_market.market_data.types import CoinData


class CoinsService:
    """
    Public API for crypto_coins module consumers.

    See module docstring for design rationale.
    """

    def __init__(self, market_service, db_service, logger=None):
        self._market = market_service
        self._db = db_service
        self._logger = logger

    # ==========================================================
    # Queries
    # ==========================================================
    async def get_coins(
        self, canonicals: Optional[list[str]] = None
    ) -> list[CoinData]:
        """
        Return the current aggregated coin snapshot.

        Args:
            canonicals: Optional filter list (uppercase). None → all.

        Returns:
            List of CoinData. Empty if no poll cycle has completed
            yet (e.g., no provider has been registered, or no UI is
            active and the poller has not run).
        """
        try:
            return await self._market.get_coins(canonicals=canonicals)
        except Exception as exc:
            self._log(
                f"get_coins failed: {exc}", level="ERROR"
            )
            return []

    async def get_coin(
        self, canonical: str
    ) -> Optional[CoinData]:
        """Return one CoinData by canonical, or None."""
        if not canonical:
            return None
        try:
            return await self._market.get_coin(canonical)
        except Exception as exc:
            self._log(
                f"get_coin({canonical}) failed: {exc}", level="ERROR"
            )
            return None

    async def refresh_now(self, force: bool = False) -> bool:
        """
        Trigger an immediate poll cycle (via crypto_market).

        Returns True if a cycle ran, False if debounced.
        """
        try:
            return await self._market.refresh_now(force=force)
        except Exception as exc:
            self._log(
                f"refresh_now failed: {exc}", level="ERROR"
            )
            return False

    def has_data(self) -> bool:
        """True if at least one poll cycle has completed."""
        try:
            return bool(self._market.has_data())
        except Exception:
            return False

    # ==========================================================
    # Introspection
    # ==========================================================
    def info(self) -> dict:
        """Serializable status summary."""
        return {
            "market": self._market.info()
            if hasattr(self._market, "info") else {},
        }

    # ==========================================================
    # Internal
    # ==========================================================
    def _log(self, message: str, level: str = "INFO") -> None:
        if self._logger:
            try:
                self._logger.log(
                    message, level=level, tag="crypto_coins"
                )
            except Exception:
                pass

    def __repr__(self) -> str:
        return "CoinsService()"


__all__ = ["CoinsService"]
