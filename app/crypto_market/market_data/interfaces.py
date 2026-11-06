"""
interfaces — provider contract for the crypto_market data layer.

Every provider (Nobitex, CoinGecko, FX, future additions) must
implement `BaseCryptoProvider`. The aggregator only knows this
interface — it never imports a concrete provider.

Numeric types
-------------
Prices and volumes are `Decimal` (financial precision — avoids the
cumulative rounding errors of `float`). Percentage changes are `float`
(they are inherently approximate; 15 significant digits add no value
and complicate serialization to JSON).

Timestamp types
---------------
Kline timestamps are UNIX epoch **milliseconds** (an integer), the
de-facto standard across financial APIs (Nobitex, Binance, CoinGecko
OHLC, TradingView's UDF). Consumer code can convert with
`datetime.fromtimestamp(ts / 1000, tz=timezone.utc)`.

Capability constants
--------------------
A provider advertises what it can do via `capabilities`, a set of
strings. The aggregator checks membership before calling the
corresponding method. Using string constants (rather than an Enum)
keeps provider implementations free of imports from this module
beyond `BaseCryptoProvider` itself.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


# ----------------------------------------------------------
# Capability constants
# ----------------------------------------------------------
# A provider that can serve `fetch_coins` advertises CAP_COINS.
# Same pattern for the other methods. The aggregator uses these
# to skip providers that cannot serve a given request kind.
CAP_COINS     = "coins"
CAP_KLINES    = "klines"
CAP_ORDERBOOK = "orderbook"


# ----------------------------------------------------------
# Data transfer objects
# ----------------------------------------------------------
@dataclass
class ProviderCoin:
    """
    A single coin price observation from one provider for one quote pair.

    A provider may return several ProviderCoin rows for the same canonical
    (e.g. Nobitex returns BTC in both USDT and RLS). The aggregator merges
    them into a single CoinData via FX conversion.

    Fields:
        canonical:   Canonical symbol, uppercase, e.g. "BTC".
        provider:    Provider name, e.g. "nobitex".
        symbol:      Provider's own symbol, e.g. "btc".
        quote:       Quote currency, e.g. "USDT", "RLS", "USD".
                     Empty string "" is only used by providers that
                     report absolute rates (e.g. an FX source that
                     reports USD→RLS as one number — it sets
                     canonical="USD", quote="RLS").
        price:       Latest price (quote units per 1 canonical unit).
        change_24h:  Percent change over the last 24h, if available.
        volume_24h:  24h volume in canonical units, if available.
        high_24h:    24h high, if available.
        low_24h:     24h low, if available.
        name:        Human-readable name ("Bitcoin"), if available.
        icon_url:    Icon URL, if available.
        updated_at:  When the provider observed this data (provider time).
        extra:       Provider-specific fields preserved for debugging or
                     future features. Consumers should not depend on
                     keys here — they are provider-defined.
    """
    canonical:  str
    provider:   str
    symbol:     str
    quote:      str
    price:      Decimal
    change_24h: Optional[float]   = None
    volume_24h: Optional[Decimal] = None
    high_24h:   Optional[Decimal] = None
    low_24h:    Optional[Decimal] = None
    name:       Optional[str]     = None
    icon_url:   Optional[str]     = None
    updated_at: Optional[datetime] = None
    extra:      dict = field(default_factory=dict)


@dataclass
class Kline:
    """
    A single OHLCV candle.

    Attributes:
        timestamp: Candle start time, UNIX epoch **milliseconds**.
        open, high, low, close:
                   Prices (Decimal).
        volume:    Volume in base-asset units (Decimal).
    """
    timestamp: int
    open:      Decimal
    high:      Decimal
    low:       Decimal
    close:     Decimal
    volume:    Decimal


@dataclass
class OrderbookLevel:
    """A single price level in an orderbook."""
    price:  Decimal
    amount: Decimal


@dataclass
class Orderbook:
    """
    Top-of-book snapshot from one provider for one canonical/quote pair.

    Levels are ordered best-first (bids descending by price, asks
    ascending by price), as the provider returned them.
    """
    canonical:  str
    provider:   str
    quote:      str
    bids:       list[OrderbookLevel]
    asks:       list[OrderbookLevel]
    updated_at: Optional[datetime] = None


# ----------------------------------------------------------
# Provider contract
# ----------------------------------------------------------
class BaseCryptoProvider(ABC):
    """
    Contract implemented by every crypto data provider.

    Lifecycle
    ---------
    A provider is instantiated by its owning module (see
    crypto_providers.providers.<name>.provider) and registered into
    `context.services` under a name of the form:

        crypto_provider_<name>

    e.g. `crypto_provider_nobitex`, `crypto_provider_coingecko`.
    The aggregator discovers providers by scanning context.services
    at `ON_ALL_MODULES_STARTED` (see market_data.registry).

    Errors
    ------
    Implementations SHOULD raise `ProviderError` (future) or return
    an empty list/None for transient failures. The aggregator
    tolerates partial failure: a provider that raises is skipped for
    that poll cycle, and other providers continue.

    Fetch methods are `async` because all providers are I/O bound
    (HTTP or WebSocket). Synchronous implementations are not allowed.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier, lowercase (e.g. "nobitex")."""

    @property
    @abstractmethod
    def capabilities(self) -> set[str]:
        """
        Capability set. Members are the CAP_* constants in this module:

            CAP_COINS     — provider implements fetch_coins
            CAP_KLINES    — provider implements fetch_klines
            CAP_ORDERBOOK — provider implements fetch_orderbook

        The aggregator only calls a method if its capability is in
        this set. A provider may implement some methods but leave
        others as the default (raising or returning empty).
        """

    @property
    @abstractmethod
    def supported_quotes(self) -> set[str]:
        """
        Quote currencies this provider can quote against.

        Examples:
            Nobitex:    {"USDT", "RLS"}
            CoinGecko:  {"USD"}
            FX:         {"RLS"}   (canonical="USD", quote="RLS")

        The aggregator uses this to decide which providers can
        contribute to a given target quote (after FX conversion).
        """

    # ------------------------------------------------------------------
    # Data fetches
    # ------------------------------------------------------------------
    @abstractmethod
    async def fetch_coins(
        self, symbols: Optional[list[str]] = None
    ) -> list[ProviderCoin]:
        """
        Fetch latest prices for one or more canonical coins.

        Parameters
        ----------
        symbols:
            Optional list of canonical symbols (uppercase). If None,
            the provider returns all coins it currently tracks. If a
            list, the provider returns rows only for those symbols
            (unknown symbols are silently skipped — not an error).

        Returns
        -------
        list[ProviderCoin]
            One row per (canonical, quote) pair. A provider that
            supports multiple quotes (e.g. Nobitex with USDT and RLS)
            returns one row per quote.

        Errors
        ------
        On transient failure, implementations should raise. The
        aggregator catches, logs, and skips this provider for the
        current cycle.
        """

    @abstractmethod
    async def fetch_klines(
        self,
        canonical: str,
        quote: str,
        interval: str,
        limit: int = 100,
    ) -> list[Kline]:
        """
        Fetch OHLCV candles.

        Parameters
        ----------
        canonical:  Uppercase canonical symbol (e.g. "BTC").
        quote:      Quote currency (e.g. "USDT").
        interval:   Provider-specific interval string. Concrete
                    providers should document their accepted values.
                    Convention across the project:
                        "5m", "15m", "1h", "4h", "1d"
                    Providers map internally as needed (e.g. Nobitex
                    UDF expects minutes as an integer).
        limit:      Maximum number of candles, ordered oldest-first.
                    Providers may cap this; the response must respect
                    ordering.

        Returns
        -------
        list[Kline]
            Oldest-first. Empty list if the pair is unknown or no
            data is available in the requested range.
        """

    async def fetch_orderbook(
        self,
        canonical: str,
        quote: str,
        depth: int = 10,
    ) -> Optional[Orderbook]:
        """
        Fetch top-of-book snapshot.

        This method is OPTIONAL. Default implementation returns None.
        Providers that support it should:
            • Add CAP_ORDERBOOK to `capabilities`.
            • Override this method.

        Parameters
        ----------
        canonical:  Uppercase canonical symbol.
        quote:      Quote currency.
        depth:      Maximum levels per side.

        Returns
        -------
        Orderbook or None
            None if the provider does not support orderbooks or has
            no data for the pair.
        """
        return None
