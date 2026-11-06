"""
crypto_market Module

Core crypto market data layer for the Ramz application.

This module has NO UI. It exposes a single service
(`crypto_market_service`) that other modules consume via
`context.services.get("crypto_market_service")`.

Internal structure:
    market_data/     — provider interface, registry, aggregator, presence, poller
    market_service/  — public API for consuming modules, background workers
    repositories/    — DB access for symbol map and (future) price history

This file is a skeleton. Service registration and background tasks are
introduced incrementally in later tasks:

    TASK 76.9  — symbol_map_repository
    TASK 76.10 — market_data.interfaces (BaseCryptoProvider)
    TASK 76.11 — market_data.registry (provider discovery)
    TASK 76.12 — market_data.presence (PresenceRegistry)
    TASK 76.13 — market_data.aggregator (merge logic)
    TASK 76.14 — market_data.poller (conditional background loop)
    TASK 76.15 — market_service.api (CryptoMarketService)
    TASK 76.16-76.18 — routes (presence, coins, klines)
    TASK 76.19 — schema migration v10→v11
"""
from massir.core.interfaces import IModule, ModuleContext


class CryptoMarketModule(IModule):
    """crypto_market module — data layer only, no UI."""

    async def start(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")

        if logger:
            logger.log(
                "crypto_market module starting…",
                tag="crypto_market",
            )

        # Services and background tasks are registered in later tasks.
        # See the module docstring above for the full sequence.

        if logger:
            logger.log(
                "crypto_market module started (skeleton — no services yet)",
                tag="crypto_market",
            )

    async def stop(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")

        if logger:
            logger.log(
                "crypto_market module stopped",
                tag="crypto_market",
            )
