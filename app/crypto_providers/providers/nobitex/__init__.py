"""
Nobitex provider — public market data from Nobitex (Iranian exchange).

Endpoints used (public only, no auth required):
    GET https://apiv2.nobitex.ir/market/stats
        All market pairs with latest price, 24h change, etc.
        Rate limit: 20 req/min per IP (per Nobitex docs).

Future (TASK 78.5+ for klines, later for authenticated endpoints):
    GET /market/udf/history       — OHLCV candles (TradingView UDF)
    GET /v3/orderbook/{symbol}    — top-of-book
    GET /v2/depth/{symbol}        — depth (for charts)
    GET /v2/trades/{symbol}       — recent trades

Authenticated endpoints (later tasks, requires user credentials):
    /orders/add, /users/wallets/list, etc.
"""
