"""
Nobitex provider — implements BaseCryptoProvider.

This module imports `app.crypto_market.market_data.interfaces` directly.
This is the ONE authorized exception to the "no direct import between
modules" rule in Ramz. Rationale: the interface is a **public contract**
that any provider plugin must implement. Importing the contract is not
the same as importing implementation — it does not couple
crypto_providers to crypto_market's runtime behavior, only to its type
signatures.

Internal implementation modules of crypto_market (registry, poller,
aggregator, presence, types) MUST NOT be imported by providers.

Data sources
------------
    /market/stats  →  fetch_coins   (implemented here)
    /market/udf/history  →  fetch_klines   (stub for now; phase 4)
    orderbook → not supported (no CAP_ORDERBOOK in capabilities)

Rate limiting
-------------
The client (client.py) enforces the rate limit internally. This
provider does not need to.

Error model
-----------
`fetch_coins` never raises. On any error it logs and returns an empty
list — the poller treats this as "provider failed for this cycle" and
continues with the others. This matches BaseCryptoProvider's docstring
contract.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.crypto_market.market_data.interfaces import (
    BaseCryptoProvider,
    CAP_COINS,
    Kline,
    ProviderCoin,
)

from .symbols import (
    canonical_to_symbol,
    is_supported_quote,
    parse_market_key,
)


PROVIDER_NAME = "nobitex"
SUPPORTED_QUOTES = frozenset({"USDT", "RLS"})


class NobitexProvider(BaseCryptoProvider):
    """
    Nobitex public market data provider.

    See module docstring for the import contract and error model.

    Constructor receives a client duck-typed to `get_market_stats()`.
    The client is NOT imported here, so provider.py can be imported
    even when `httpx` is not installed (though `fetch_coins` would
    then fail at call time — moot because `module.start()` only
    constructs the provider when the client imports successfully).
    """

    def __init__(self, client, logger=None):
        self._client = client
        self._logger = logger

    # ==========================================================
    # Identity
    # ==========================================================
    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def capabilities(self) -> set[str]:
        # Orderbook and klines are NOT advertised — fetch_klines is
        # a stub below, and fetch_orderbook inherits the default
        # (returns None). Advertising a capability we don't really
        # implement would mislead the aggregator.
        return frozenset({CAP_COINS})

    @property
    def supported_quotes(self) -> set[str]:
        return SUPPORTED_QUOTES

    # ==========================================================
    # Fetch
    # ==========================================================
    async def fetch_coins(
        self, symbols: Optional[list[str]] = None
    ) -> list[ProviderCoin]:
        """
        Fetch latest prices from Nobitex /market/stats.

        Args:
            symbols: Optional list of canonical symbols (uppercase,
                e.g. ["BTC", "ETH"]). None → all markets.

        Returns:
            One ProviderCoin per supported (canonical, quote) pair.
            Empty list on any error.
        """
        try:
            stats = await self._client.get_market_stats()
        except Exception as exc:
            self._log(
                f"fetch_coins: client raised: {exc}",
                level="WARNING",
            )
            return []

        if not stats:
            return []

        wanted: Optional[set[str]] = None
        if symbols:
            wanted = set()
            for s in symbols:
                if isinstance(s, str):
                    s = s.strip().upper()
                    if s:
                        wanted.add(s)
            if not wanted:
                wanted = None

        result: list[ProviderCoin] = []
        skipped_invalid_key = 0
        skipped_unsupported = 0
        skipped_invalid_data = 0

        for key, entry in stats.items():
            if not isinstance(entry, dict):
                skipped_invalid_data += 1
                continue

            parsed = parse_market_key(key)
            if not parsed:
                skipped_invalid_key += 1
                continue
            canonical, quote = parsed

            if not is_supported_quote(quote):
                skipped_unsupported += 1
                continue

            if wanted is not None and canonical not in wanted:
                continue

            coin = self._build_provider_coin(
                canonical, quote, entry
            )
            if coin is None:
                skipped_invalid_data += 1
                continue
            result.append(coin)

        if skipped_invalid_key or skipped_unsupported or skipped_invalid_data:
            self._log(
                f"fetch_coins: skipped "
                f"{skipped_invalid_key} invalid keys, "
                f"{skipped_unsupported} unsupported quotes, "
                f"{skipped_invalid_data} invalid entries",
                level="DEBUG",
            )

        return result

    async def fetch_klines(
        self,
        canonical: str,
        quote: str,
        interval: str,
        limit: int = 100,
    ) -> list[Kline]:
        """
        Not implemented yet (phase 4 — crypto_charts).

        Returns []. Does NOT advertise CAP_KLINES, so callers should
        not reach this method through `registry.by_capability`. The
        stub exists only because the base class marks it abstract.
        """
        self._log(
            f"fetch_klines not implemented for Nobitex "
            f"(canonical={canonical}, quote={quote}, "
            f"interval={interval}, limit={limit}); returning []",
            level="DEBUG",
        )
        return []

    # fetch_orderbook is inherited (returns None); CAP_ORDERBOOK is
    # not advertised.

    # ==========================================================
    # Introspection
    # ==========================================================
    def info(self) -> dict:
        return {
            "name":           self.name,
            "capabilities":   sorted(self.capabilities),
            "supported_quotes": sorted(self.supported_quotes),
        }

    # ==========================================================
    # Internal
    # ==========================================================
    def _build_provider_coin(
        self, canonical: str, quote: str, entry: dict
    ) -> Optional[ProviderCoin]:
        """
        Build a ProviderCoin from one Nobitex stats entry, or None.

        Nobitex /market/stats entry shape (fields we use):
            {
                "latest":      "67000.5",   // last price (required)
                "dayChange":   "2.45",      // 24h change %
                "dayHigh":     "67500.0",
                "dayLow":      "66800.0",
                "volumeSrc":   "123.45",    // volume in source (canonical)
                "volumeDst":   "8250000.0", // volume in dest (quote)
            }

        Any of the optional fields may be missing or invalid; we
        degrade gracefully.
        """
        price = self._parse_decimal(entry.get("latest"))
        if price is None:
            return None

        change = self._parse_float(entry.get("dayChange"))
        high = self._parse_decimal(entry.get("dayHigh"))
        low = self._parse_decimal(entry.get("dayLow"))

        # Prefer volumeSrc (canonical units); fall back to volumeDst.
        volume = self._parse_decimal(entry.get("volumeSrc"))
        if volume is None:
            volume = self._parse_decimal(entry.get("volumeDst"))

        return ProviderCoin(
            canonical=canonical,
            provider=PROVIDER_NAME,
            symbol=canonical_to_symbol(canonical),
            quote=quote,
            price=price,
            change_24h=change,
            volume_24h=volume,
            high_24h=high,
            low_24h=low,
            name=None,
            icon_url=None,
            updated_at=datetime.utcnow(),
        )

    @staticmethod
    def _parse_decimal(value) -> Optional[Decimal]:
        """
        Parse a Decimal from Nobitex's string field, rejecting
        non-positive values (used for prices and volumes).
        """
        if value is None:
            return None
        try:
            d = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None
        if not d.is_finite() or d <= 0:
            return None
        return d

    @staticmethod
    def _parse_float(value) -> Optional[float]:
        """Parse a float from Nobitex's string field (change %)."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

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
            f"NobitexProvider("
            f"capabilities={sorted(self.capabilities)}, "
            f"quotes={sorted(self.supported_quotes)})"
        )


__all__ = ["NobitexProvider", "PROVIDER_NAME", "SUPPORTED_QUOTES"]
