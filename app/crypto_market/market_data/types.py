"""
types — consumer-facing DTOs produced by the aggregator.

Layering
--------
    interfaces.py   provider-facing types  (input from providers)
    types.py        consumer-facing types  (output of aggregator)

Providers return `ProviderCoin`, `Kline`, `Orderbook` (interfaces.py).
The aggregator merges provider rows into `CoinData` (this module),
which is what the public service (`market_service.api`) hands to
consuming modules (`crypto_coins`, `crypto_charts`).

Data model (design intent)
--------------------------
`CoinData` preserves the price reported by EVERY provider — it does
not collapse multiple providers into a single value. The UI is
expected to render each provider's price in its own column and a
"Spread %" column from `price_dispersion_pct`.

`reference_prices` is a derived value (median per quote, FX-converted).
It exists for:

    • meaningful cross-provider comparison (after normalizing quotes),
    • charting / analysis (which wants one clean number per quote),
    • a stable "as of" value for consumers that do not care about
      provider-level details.

Consumers who only want a single number per quote should read
`reference_prices`; consumers who want to show provider columns read
`provider_prices`.

Keep this file free of provider-specific types and of any aggregation
logic.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class ProviderPrice:
    """
    A single provider's observation for one (canonical, quote) pair.

    A provider that reports the same canonical in multiple quotes (e.g.
    Nobitex reporting BTC in both USDT and RLS) produces one
    ProviderPrice per quote. A provider that reports a coin in only one
    quote (e.g. CoinGecko reporting BTC in USD) produces one
    ProviderPrice.
    """
    provider:   str
    quote:      str
    price:      Decimal
    change_24h: Optional[float]   = None
    volume_24h: Optional[Decimal] = None
    updated_at: Optional[datetime] = None


@dataclass
class CoinData:
    """
    Aggregated view of a single coin, preserving per-provider prices.

    Fields
    ------
    canonical:
        Uppercase canonical symbol, e.g. "BTC".

    provider_prices:
        Mapping of provider name → list of ProviderPrice rows.
        Multiple entries per provider when the provider reports the
        coin in multiple quotes. Sorted stably by (provider, quote)
        at aggregation time.

    reference_prices:
        Mapping of quote → Decimal. One value per quote, computed as
        the median of all providers that reported that quote, plus
        FX-derived fill-ins for target quotes that no provider
        reported. This is the value consumers should use when they
        need one number per quote (e.g. charts, ranking by price).

    price_dispersion_pct:
        Mapping of quote → Optional[float]. The value is
        (max_price - min_price) / median_price * 100 across all
        providers that reported that quote. None when fewer than two
        providers reported that quote, or when the median is zero.

    available_quotes:
        Sorted list of quotes present in `reference_prices`.
        JSON-friendly (a list, not a set).

    name, symbol_display, icon_url:
        Optional display metadata, best-effort from any provider row.

    sources:
        Sorted list of provider names that contributed to this coin.

    updated_at:
        Latest timestamp among all provider rows (provider time).
    """
    canonical: str

    provider_prices:      dict[str, list[ProviderPrice]] = field(default_factory=dict)
    reference_prices:     dict[str, Decimal]             = field(default_factory=dict)
    price_dispersion_pct: dict[str, Optional[float]]     = field(default_factory=dict)
    available_quotes:     list[str]                      = field(default_factory=list)

    name:           Optional[str] = None
    symbol_display: Optional[str] = None
    icon_url:       Optional[str] = None

    sources:    list[str]           = field(default_factory=list)
    updated_at: Optional[datetime]  = None


__all__ = ["ProviderPrice", "CoinData"]
