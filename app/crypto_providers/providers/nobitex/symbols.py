"""
symbols — Nobitex market-key helpers.

Nobitex `/market/stats` returns a dict keyed by market name in the form
`<coin>-<quote>`, all lowercase, e.g.:

    "btc-rls":  {...}
    "btc-usdt": {...}
    "eth-rls":  {...}

This module provides pure-string helpers to convert between that key
format and the project's (canonical, quote) representation.

Nothing here touches the network or the DB. No caching. No side
effects. Consumers (provider.py in TASK 78.5) compose these helpers
with the API response.

`crypto_symbol_map` (the DB table) is NOT used here. Nobitex symbols
are a simple lowercase transform of the canonical, so a DB round-trip
would be pure overhead. When a provider with a non-trivial symbol
mapping is added (CoinGecko uses "bitcoin" for "BTC"), the symbol_map
repository will be more useful — but even there, CoinGecko provides
the mapping directly via the `id` field in its API response, so the
DB may never be necessary for these two providers. It remains
available for future providers with no in-band mapping.
"""
from typing import Optional


# Quote currencies supported by Nobitex /market/stats.
# RLS = Rial, USDT = Tether. IRT (Toman) is not currently used
# as a market quote in the public API.
SUPPORTED_QUOTES = frozenset({"USDT", "RLS"})


def parse_market_key(key: str) -> Optional[tuple[str, str]]:
    """
    Parse a Nobitex market key into (canonical, quote).

    Examples:
        "btc-rls"   → ("BTC", "RLS")
        "eth-usdt"  → ("ETH", "USDT")
        "usdt-rls"  → ("USDT", "RLS")   # valid: USDT is also a canonical

    Returns None if the key is malformed (no hyphen, empty parts,
    extra hyphens in unexpected positions).

    The returned quote is uppercased but not validated against
    SUPPORTED_QUOTES — callers may want to log unknown quotes rather
    than drop them silently.
    """
    if not key or not isinstance(key, str):
        return None
    parts = key.lower().split("-", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return (parts[0].upper(), parts[1].upper())


def build_market_key(canonical: str, quote: str) -> str:
    """
    Build a Nobitex market key from (canonical, quote).

    "BTC", "RLS" → "btc-rls"
    "ETH", "USDT" → "eth-usdt"

    No validation is performed; both parts are stripped and lowercased.
    """
    return f"{canonical.strip().lower()}-{quote.strip().lower()}"


def canonical_to_symbol(canonical: str) -> str:
    """
    Convert a canonical symbol to Nobitex's symbol (lowercase).

    "BTC" → "btc"
    """
    return canonical.strip().lower()


def symbol_to_canonical(symbol: str) -> str:
    """
    Convert a Nobitex symbol to canonical (uppercase).

    "btc" → "BTC"
    """
    return symbol.strip().upper()


def is_supported_quote(quote: str) -> bool:
    """True if `quote` (case-insensitive) is in SUPPORTED_QUOTES."""
    if not quote:
        return False
    return quote.strip().upper() in SUPPORTED_QUOTES


__all__ = [
    "SUPPORTED_QUOTES",
    "parse_market_key",
    "build_market_key",
    "canonical_to_symbol",
    "symbol_to_canonical",
    "is_supported_quote",
]
