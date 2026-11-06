"""
market_data — internal data layer for crypto_market.

This package contains:
    interfaces.py  — BaseCryptoProvider ABC (TASK 76.10)
    registry.py    — provider discovery from context.services (TASK 76.11)
    presence.py    — PresenceRegistry (TASK 76.12)
    aggregator.py  — multi-source merge + FX conversion (TASK 76.13)
    poller.py      — conditional background loop (TASK 76.14)

Not intended for direct import from outside crypto_market.
External consumers use `crypto_market_service` (market_service.api).
"""
