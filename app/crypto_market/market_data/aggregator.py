"""
aggregator — build CoinData from provider observations.

Responsibilities
----------------
Given a flat list of `ProviderCoin` rows collected by the poller, this
module produces one `CoinData` per canonical coin, with:

    • provider_prices      — every price reported by every provider
    • reference_prices     — median per quote, FX-normalized
    • price_dispersion_pct — (max − min) / median × 100 per quote
    • available_quotes     — sorted quotes in reference_prices

Non-responsibilities
--------------------
    • Fetching (poller's job).
    • Sorting by volume / market cap (consumer's job).
    • Filtering by user preference (service's job).
    • Deciding which provider "wins" — there is no winner. Every
      provider's price is preserved in `provider_prices`.

Design intent
-------------
The UI is expected to display each provider's price in its own column
plus a "Spread %" column fed by `price_dispersion_pct`. The aggregator
must therefore retain every observation, not collapse to one value.

`reference_prices` is a derived convenience (median per quote, FX-
converted) for consumers that want a single number (charts, ranking,
analysis).

FX conversion
-------------
FX rates are conveyed as ordinary `ProviderCoin` rows where both
`canonical` and `quote` are currency codes. Example:

    ProviderCoin(canonical="USD", quote="RLS", price=Decimal("900000"))

means "1 USD = 900,000 RLS". The aggregator:

    1. Extracts the USD↔RLS rate (handles both orientations).
    2. Uses USDT ≈ USD (industry convention; divergence <1%).
    3. Fills missing target quotes in `reference_prices` only.
       Raw provider rows in `provider_prices` are never modified.

The USDT ≈ USD approximation is documented here. If a future version
needs stricter handling, extend `_fill_quotes` with an explicit
usdt_usd rate.

Currency exclusion
------------------
Currencies (USD, RLS, IRR, EUR, ...) appear as canonicals in raw
provider rows (from FX providers). They are NOT coins and must not
appear in CoinData. `DEFAULT_CURRENCY_CANONICALS` is the exclusion
list. USDT is intentionally NOT excluded — on Nobitex it is both a
tradable coin and a quote currency.
"""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Optional

from .interfaces import ProviderCoin
from .types import CoinData, ProviderPrice


DEFAULT_CURRENCY_CANONICALS = frozenset({
    "USD", "RLS", "IRR", "EUR", "GBP", "AED", "TRY",
})

# Target quotes the aggregator always tries to populate in
# `reference_prices`. Quotes reported by providers but not listed here
# are preserved in `reference_prices` as-is (median only, no FX fill).
TARGET_QUOTES = ("USDT", "RLS", "USD")


class Aggregator:
    """
    Builds CoinData from raw provider rows.

    Instantiated once by crypto_market (see market_service/api.py).
    Stateless across calls — `aggregate()` can be called concurrently
    from different coroutines as long as the input list is not mutated
    during iteration (the poller passes a fresh list per cycle).
    """

    def __init__(
        self,
        logger=None,
        currency_canonicals: Optional[frozenset] = None,
    ):
        self._logger = logger
        self._currency_canonicals = (
            currency_canonicals
            if currency_canonicals is not None
            else DEFAULT_CURRENCY_CANONICALS
        )

    # ----------------------------------------------------------
    # Public
    # ----------------------------------------------------------
    def aggregate(self, provider_coins: list[ProviderCoin]) -> list[CoinData]:
        """
        Build per-canonical CoinData from raw provider rows.

        Args:
            provider_coins: Flat list of rows from all providers for
                the current poll cycle. Order is irrelevant.

        Returns:
            One CoinData per non-currency canonical. Unordered.
            Empty list if input is empty or contains only currency
            rows.
        """
        if not provider_coins:
            return []

        # 1. Extract FX rate (USD → RLS) if present
        fx_usd_rls = self._extract_fx_usd_rls(provider_coins)

        # 2. Group non-currency rows by canonical
        by_canonical: dict[str, list[ProviderCoin]] = defaultdict(list)
        for pc in provider_coins:
            if not pc or not pc.canonical:
                continue
            if pc.canonical in self._currency_canonicals:
                continue
            by_canonical[pc.canonical].append(pc)

        if not by_canonical:
            return []

        # 3. Build CoinData per canonical
        result: list[CoinData] = []
        for canonical, rows in by_canonical.items():
            coin = self._build_coin_data(canonical, rows, fx_usd_rls)
            if coin is not None:
                result.append(coin)

        return result

    # ----------------------------------------------------------
    # Per-canonical build
    # ----------------------------------------------------------
    def _build_coin_data(
        self,
        canonical: str,
        rows: list[ProviderCoin],
        fx_usd_rls: Optional[Decimal],
    ) -> Optional[CoinData]:
        """
        Build one CoinData from all rows for a single canonical.
        Returns None only if `rows` is empty (defensive).
        """
        if not rows:
            return None

        # --- 1. provider_prices (every observation kept) ---
        provider_prices: dict[str, list[ProviderPrice]] = defaultdict(list)
        sources: set[str] = set()
        latest_updated_at: Optional[datetime] = None

        for pc in rows:
            provider_prices[pc.provider].append(ProviderPrice(
                provider=pc.provider,
                quote=pc.quote,
                price=pc.price,
                change_24h=pc.change_24h,
                volume_24h=pc.volume_24h,
                updated_at=pc.updated_at,
            ))
            if pc.provider:
                sources.add(pc.provider)
            if pc.updated_at is not None:
                if latest_updated_at is None or pc.updated_at > latest_updated_at:
                    latest_updated_at = pc.updated_at

        # Sort each provider's prices stably by quote for a deterministic
        # JSON output. Consumers can rely on this ordering.
        for provider_name in provider_prices:
            provider_prices[provider_name].sort(key=lambda pp: pp.quote)

        # --- 2. Prices grouped by quote, across providers ---
        prices_by_quote: dict[str, list[Decimal]] = defaultdict(list)
        for pc in rows:
            prices_by_quote[pc.quote].append(pc.price)

        # --- 3. reference_prices (median per quote) ---
        reference_prices: dict[str, Decimal] = {}
        for quote, prices in prices_by_quote.items():
            reference_prices[quote] = self._median(prices)

        # --- 4. price_dispersion_pct (max−min)/median × 100 per quote) ---
        price_dispersion_pct: dict[str, Optional[float]] = {}
        for quote, prices in prices_by_quote.items():
            price_dispersion_pct[quote] = self._dispersion(
                prices, reference_prices[quote]
            )

        # --- 5. FX fill (only reference_prices is modified) ---
        reference_prices = self._fill_quotes(reference_prices, fx_usd_rls)

        # --- 6. available_quotes (sorted, JSON-friendly) ---
        available_quotes = sorted(reference_prices.keys())

        # --- 7. Metadata (best-effort from any row) ---
        name, icon_url = self._pick_metadata(rows)

        return CoinData(
            canonical=canonical,
            provider_prices=dict(provider_prices),
            reference_prices=reference_prices,
            price_dispersion_pct=price_dispersion_pct,
            available_quotes=available_quotes,
            name=name,
            symbol_display=canonical,
            icon_url=icon_url,
            sources=sorted(sources),
            updated_at=latest_updated_at,
        )

    # ----------------------------------------------------------
    # Metadata
    # ----------------------------------------------------------
    def _pick_metadata(
        self, rows: list[ProviderCoin]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Best-effort extraction of name and icon_url from any row.

        Providers that report these (CoinGecko) supply them; providers
        that don't (Nobitex) leave them None. First non-empty value wins.
        """
        name: Optional[str] = None
        icon_url: Optional[str] = None
        for pc in rows:
            if name is None and pc.name:
                name = pc.name
            if icon_url is None and pc.icon_url:
                icon_url = pc.icon_url
            if name is not None and icon_url is not None:
                break
        return name, icon_url

    # ----------------------------------------------------------
    # Statistics
    # ----------------------------------------------------------
    def _median(self, prices: list[Decimal]) -> Decimal:
        """
        Median of a non-empty list of Decimal values.

        For even-length lists, returns the arithmetic mean of the two
        middle values (standard statistical definition). Callers must
        guarantee a non-empty list; `prices_by_quote` entries are
        created only when at least one price was appended.
        """
        sorted_prices = sorted(prices)
        n = len(sorted_prices)
        if n % 2 == 1:
            return sorted_prices[n // 2]
        a = sorted_prices[n // 2 - 1]
        b = sorted_prices[n // 2]
        return (a + b) / Decimal(2)

    def _dispersion(
        self, prices: list[Decimal], reference: Decimal
    ) -> Optional[float]:
        """
        Percent dispersion: (max − min) / median × 100.

        Returns None when:
            • fewer than two observations (no spread to measure),
            • reference is zero (would divide by zero).

        The result is a `float` because percent values are inherently
        approximate and JSON-friendly as float.
        """
        if len(prices) < 2:
            return None
        if reference is None or reference == 0:
            return None
        try:
            spread = (max(prices) - min(prices)) / reference * Decimal(100)
            return float(spread)
        except Exception:
            return None

    # ----------------------------------------------------------
    # FX
    # ----------------------------------------------------------
    def _extract_fx_usd_rls(
        self, coins: list[ProviderCoin]
    ) -> Optional[Decimal]:
        """
        Return "how many RLS per 1 USD", handling both orientations.

        • (canonical="USD", quote="RLS", price=X)   → X
        • (canonical="RLS", quote="USD", price=Y>0) → 1 / Y

        Returns None if no FX rate is available.
        """
        for pc in coins:
            if not pc or not pc.canonical or not pc.quote:
                continue
            if pc.canonical == "USD" and pc.quote == "RLS":
                return pc.price
            if pc.canonical == "RLS" and pc.quote == "USD":
                if pc.price > 0:
                    return Decimal(1) / pc.price
        return None

    def _fill_quotes(
        self,
        reference_prices: dict[str, Decimal],
        fx_usd_rls: Optional[Decimal],
    ) -> dict[str, Decimal]:
        """
        Fill missing target quotes in `reference_prices` via FX.

        Only `reference_prices` is modified. `provider_prices` is
        never touched — provider observations are always raw.

        Approximation: USDT ≈ USD.
        """
        result = dict(reference_prices)

        # 1. USDT ≈ USD (identity)
        if "USD" in result and "USDT" not in result:
            result["USDT"] = result["USD"]
        if "USDT" in result and "USD" not in result:
            result["USD"] = result["USDT"]

        # 2. Cross-quote via RLS if FX is available
        if fx_usd_rls is None or fx_usd_rls <= 0:
            return result

        if "RLS" not in result:
            if "USD" in result:
                result["RLS"] = result["USD"] * fx_usd_rls
            elif "USDT" in result:
                result["RLS"] = result["USDT"] * fx_usd_rls

        if "RLS" in result:
            if "USD" not in result:
                result["USD"] = result["RLS"] / fx_usd_rls
            if "USDT" not in result:
                result["USDT"] = result["RLS"] / fx_usd_rls

        return result

    # ----------------------------------------------------------
    # Internal
    # ----------------------------------------------------------
    def _log(self, message: str, level: str = "INFO") -> None:
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="crypto_market")
            except Exception:
                pass

    def __repr__(self) -> str:
        return (
            f"Aggregator(currencies={len(self._currency_canonicals)})"
        )


__all__ = [
    "Aggregator",
    "DEFAULT_CURRENCY_CANONICALS",
    "TARGET_QUOTES",
]
