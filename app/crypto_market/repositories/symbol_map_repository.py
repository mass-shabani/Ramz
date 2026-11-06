"""
symbol_map_repository — CRUD for the `crypto_symbol_map` table.

The table maps:
    canonical (e.g. "BTC")
    → provider's symbol (e.g. "btc" for Nobitex, "bitcoin" for CoinGecko)
    → provider's quote currency (e.g. "USDT", "RLS", "USD", or "" for FX)

Composite primary key: (canonical, provider, provider_quote).

`provider_quote` is always a non-NULL string (empty "" when the provider
has no quote-currency concept, e.g. an FX rate provider). This avoids
the SQLite composite-PK issue where NULL != NULL, which would break
`INSERT OR REPLACE` semantics and create duplicate rows.

The repository does NOT cache. Bulk lookups are the caller's
responsibility (see market_data.registry / aggregator, which hold an
in-memory dict refreshed by the poller).
"""
from typing import Optional


class SymbolMapRepository:
    """CRUD for crypto_symbol_map."""

    TABLE = "crypto_symbol_map"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    def _log(self, message, level="INFO"):
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="crypto_market")
            except Exception:
                pass

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_provider_symbol(
        self, canonical: str, provider: str, quote: str = ""
    ) -> Optional[str]:
        """
        Return the provider's symbol for a canonical coin, or None.

        Examples:
            get_provider_symbol("BTC", "nobitex", "USDT")   → "btc"
            get_provider_symbol("BTC", "coingecko", "")     → "bitcoin"
        """
        if not canonical or not provider:
            return None
        try:
            row = await self._conn().find_one(
                self.TABLE,
                where={
                    "canonical":      canonical,
                    "provider":       provider,
                    "provider_quote": quote or "",
                },
            )
            return row.get("provider_symbol") if row else None
        except Exception as exc:
            self._log(f"get_provider_symbol failed: {exc}", level="ERROR")
            return None

    async def get_canonical(
        self, provider: str, provider_symbol: str, quote: str = ""
    ) -> Optional[str]:
        """
        Reverse lookup: provider symbol → canonical.

        Example:
            get_canonical("nobitex", "btc", "USDT") → "BTC"
        """
        if not provider or not provider_symbol:
            return None
        try:
            row = await self._conn().find_one(
                self.TABLE,
                where={
                    "provider":        provider,
                    "provider_symbol": provider_symbol,
                    "provider_quote":  quote or "",
                },
            )
            return row.get("canonical") if row else None
        except Exception as exc:
            self._log(f"get_canonical failed: {exc}", level="ERROR")
            return None

    async def list_by_provider(self, provider: str) -> list[dict]:
        """
        Return all mappings for a provider.

        Each dict has keys: canonical, provider, provider_symbol, provider_quote.
        """
        if not provider:
            return []
        try:
            return await self._conn().find_many(
                self.TABLE, where={"provider": provider}
            )
        except Exception as exc:
            self._log(f"list_by_provider failed: {exc}", level="ERROR")
            return []

    async def list_by_canonical(self, canonical: str) -> list[dict]:
        """
        Return all mappings for a canonical coin, across all providers.
        """
        if not canonical:
            return []
        try:
            return await self._conn().find_many(
                self.TABLE, where={"canonical": canonical}
            )
        except Exception as exc:
            self._log(f"list_by_canonical failed: {exc}", level="ERROR")
            return []

    async def list_all(self) -> list[dict]:
        """Return every row in the table."""
        try:
            return await self._conn().find_many(self.TABLE, where={})
        except Exception as exc:
            self._log(f"list_all failed: {exc}", level="ERROR")
            return []

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def upsert(
        self,
        canonical: str,
        provider: str,
        provider_symbol: str,
        quote: str = "",
    ) -> bool:
        """
        Insert or update a single mapping.

        Returns True on success, False on invalid input or write error.
        """
        if not canonical or not provider or not provider_symbol:
            return False

        quote = quote or ""

        where = {
            "canonical":      canonical,
            "provider":       provider,
            "provider_quote": quote,
        }
        try:
            existing = await self._conn().find_one(self.TABLE, where=where)
            if existing:
                result = await self._conn().update(
                    self.TABLE,
                    data={"provider_symbol": provider_symbol},
                    where=where,
                )
            else:
                result = await self._conn().insert(
                    self.TABLE,
                    data={
                        "canonical":       canonical,
                        "provider":        provider,
                        "provider_symbol": provider_symbol,
                        "provider_quote":  quote,
                    },
                )
            return bool(getattr(result, "success", False))
        except Exception as exc:
            self._log(f"upsert failed: {exc}", level="ERROR")
            return False

    async def bulk_upsert(self, entries: list[dict]) -> int:
        """
        Insert or update many mappings.

        Each entry must be a dict with keys:
            canonical, provider, provider_symbol, and optionally quote.

        Returns the number of successful writes.
        """
        if not entries:
            return 0
        count = 0
        for entry in entries:
            ok = await self.upsert(
                canonical=entry.get("canonical"),
                provider=entry.get("provider"),
                provider_symbol=entry.get("provider_symbol"),
                quote=entry.get("quote", ""),
            )
            if ok:
                count += 1
        return count
