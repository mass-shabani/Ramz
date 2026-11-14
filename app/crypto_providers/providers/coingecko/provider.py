"""
CoinGecko provider — implements BaseCryptoProvider.

Imports `app.crypto_market.market_data.interfaces` directly (the ONE
authorized cross-module import — the provider contract, not the
implementation). No import of client.py: duck typing, so this file
is importable even when httpx is absent.

Data sources
------------
    /coins/markets  →  fetch_coins   (implemented here)
    klines, orderbook → not implemented (no CAP_KLINES, no CAP_ORDERBOOK)

Quote semantics
---------------
CoinGecko reports prices in the requested `vs_currency`, which we
hardcode to USD (see client.py). All ProviderCoin rows produced here
have quote="USD". The aggregator converts to USDT (identity, via the
USDT≈USD approximation documented in crypto_market/aggregator.py)
and RLS (via the FX provider).
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


PROVIDER_NAME = "coingecko"
SUPPORTED_QUOTES = frozenset({"USD"})


class CoinGeckoProvider(BaseCryptoProvider):
    """
    CoinGecko public market data provider.

    See module docstring for import contract and quote semantics.
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
        # Only coins. Klines/orderbook not implemented.
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
        Fetch top-100 coins by market cap from CoinGecko.

        Args:
            symbols: Optional list of canonical symbols (uppercase).
                If provided, only entries whose `symbol.upper()`
                matches are returned. Filtering is local — CoinGecko
                always returns the top-N list regardless.

        Returns:
            One ProviderCoin per coin (quote="USD"). Empty on error.
        """
        try:
            markets = await self._client.get_markets()
        except Exception as exc:
            self._log(
                f"fetch_coins: client raised: {exc}",
                level="WARNING",
            )
            return []

        if not markets:
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
        skipped_invalid = 0

        for entry in markets:
            if not isinstance(entry, dict):
                skipped_invalid += 1
                continue

            coin = self._build_provider_coin(entry)
            if coin is None:
                skipped_invalid += 1
                continue

            if wanted is not None and coin.canonical not in wanted:
                continue

            result.append(coin)

        if skipped_invalid:
            self._log(
                f"fetch_coins: skipped {skipped_invalid} "
                f"invalid or unpriced entries",
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
        """Not implemented yet. Returns []. Does not advertise
        CAP_KLINES, so callers should not reach this method."""
        self._log(
            f"fetch_klines not implemented for CoinGecko "
            f"(canonical={canonical}, quote={quote}, "
            f"interval={interval}, limit={limit}); returning []",
            level="DEBUG",
        )
        return []

    # fetch_orderbook inherited (returns None); CAP_ORDERBOOK not
    # advertised.

    # ==========================================================
    # Introspection
    # ==========================================================
    def info(self) -> dict:
        return {
            "name":             self.name,
            "capabilities":     sorted(self.capabilities),
            "supported_quotes": sorted(self.supported_quotes),
        }

    # ==========================================================
    # Internal
    # ==========================================================
    def _build_provider_coin(
        self, entry: dict
    ) -> Optional[ProviderCoin]:
        """
        Build a ProviderCoin from one CoinGecko /coins/markets entry,
        or None if the entry has no usable data.

        Fields we use:
            id                           — e.g. "bitcoin" (unused v1)
            symbol                       — e.g. "btc" → canonical "BTC"
            name                         — e.g. "Bitcoin"
            current_price                — USD price (Decimal)
            price_change_percentage_24h  — float or null
            total_volume                 — 24h volume in USD (Decimal)
            high_24h, low_24h            — Decimal or null
            image                        — icon URL
            last_updated                 — ISO 8601 string
        """
        symbol = entry.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            return None
        canonical = symbol.strip().upper()
        if not canonical:
            return None

        price = self._parse_decimal(entry.get("current_price"))
        if price is None:
            # CoinGecko returns null current_price for some inactive
            # or unlisted coins. Skip.
            return None

        change = self._parse_float(
            entry.get("price_change_percentage_24h")
        )
        volume = self._parse_decimal(entry.get("total_volume"))
        high = self._parse_decimal(entry.get("high_24h"))
        low = self._parse_decimal(entry.get("low_24h"))
        name = entry.get("name") if isinstance(
            entry.get("name"), str
        ) else None
        icon_url = entry.get("image") if isinstance(
            entry.get("image"), str
        ) else None
        updated_at = self._parse_iso_utc(entry.get("last_updated"))

        return ProviderCoin(
            canonical=canonical,
            provider=PROVIDER_NAME,
            symbol=symbol.strip().lower(),
            quote="USD",
            price=price,
            change_24h=change,
            volume_24h=volume,
            high_24h=high,
            low_24h=low,
            name=name,
            icon_url=icon_url,
            updated_at=updated_at,
        )

    @staticmethod
    def _parse_decimal(value) -> Optional[Decimal]:
        """
        Parse a Decimal. CoinGecko returns float for prices, so we
        accept int, float, and numeric strings.

        Rejects non-positive values (a price of 0 is not usable).
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
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_iso_utc(value) -> Optional[datetime]:
        """
        Parse CoinGecko's ISO 8601 timestamp ("2026-11-08T11:00:00.000Z")
        into a timezone-naive UTC datetime (matching what Nobitex
        produces via datetime.utcnow()).

        Returns None on any parse failure.
        """
        if not isinstance(value, str) or not value.strip():
            return None
        s = value.strip()
        # Python 3.10 doesn't accept trailing 'Z' in fromisoformat;
        # strip it. 3.11+ accepts it, but the strip is harmless there.
        if s.endswith("Z"):
            s = s[:-1]
        try:
            return datetime.fromisoformat(s)
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
            f"CoinGeckoProvider("
            f"capabilities={sorted(self.capabilities)}, "
            f"quotes={sorted(self.supported_quotes)})"
        )


__all__ = ["CoinGeckoProvider", "PROVIDER_NAME", "SUPPORTED_QUOTES"]
