"""
CoinGecko provider — public market data from CoinGecko.

Endpoint used (public, no auth required):
    GET https://api.coingecko.com/api/v3/coins/markets
        Query: vs_currency=usd, order=market_cap_desc,
               per_page=100, page=1, price_change_percentage=24h
        Rate limit: 30 req/min for the free tier (per CoinGecko docs).

This provider reports prices in USD only. Cross-quote conversion
(USD → USDT → RLS) is performed by the aggregator in crypto_market
using the FX provider, not here.

CoinGecko returns coin symbols in lowercase (e.g. "btc" for Bitcoin).
We treat `symbol.upper()` as the canonical. Collisions (rare) are
accepted in v1; a later task may introduce a static map or the
crypto_symbol_map table if needed.
"""
