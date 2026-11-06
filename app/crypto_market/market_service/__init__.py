"""
market_service — public API for crypto_market consumers.

This package contains:
    api.py      — CryptoMarketService (TASK 76.15)
    workers.py  — background task helpers (future)
    history.py  — price-history recording (future)

The service registered under `crypto_market_service` is an instance of
CryptoMarketService (api.py). External consumers should only depend on
that service's public methods.
"""
