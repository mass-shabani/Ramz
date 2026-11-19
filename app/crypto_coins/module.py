"""
crypto_coins Module

Crypto coins page module. In phase 3, this module will provide:

    • A coin list UI (partial injected into user_panel sidebar).
    • A dashboard widget (top-coins summary).
    • Per-user coin settings (favorites, display currency).

Internal structure (as it grows):
    services.py         — CoinsService (public API)
    repositories/       — user_preference_repository (TASK 79.2)
    templates/partials/ — coins_list.html, coins_settings.html
                          (TASK 79.3, 79.4)
    routes.py           — JSON + HTML partial endpoints (TASK 79.3+)

This file (TASK 79.1) registers the service only. No routes, no
templates, no extensions. UI is not affected.

Startup sequence
----------------
    start():
        1. Resolve crypto_market_service, app_db_service from context.
        2. Instantiate CoinsService.
        3. Register `crypto_coins_service` in context.services.

    Each step is fail-soft: a missing prerequisite logs an ERROR and
    the module does not register its service — the rest of the
    application keeps working (matching the project's convention).

Deployment notes
----------------
Enabling crypto_coins without crypto_market is rejected by Massir's
check_requirements (crypto_coins declares crypto_market_service in
`requires`). Disabling crypto_coins while crypto_market and
crypto_providers are enabled is valid — the data layer keeps
running (the poller keeps polling while any UI is active), the
coins UI simply does not appear.
"""
from massir.core.interfaces import IModule, ModuleContext

from .services import CoinsService


class CryptoCoinsModule(IModule):
    """
    crypto_coins module — coin list page + dashboard widget.

    Provides:
        crypto_coins_service (CoinsService)
    """

    def __init__(self):
        self._service = None

    async def start(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")

        if logger:
            logger.log(
                "crypto_coins module starting…",
                tag="crypto_coins",
            )

        # --- 1. Resolve prerequisites -------------------------
        market_service = context.services.get("crypto_market_service")
        db_service     = context.services.get("app_db_service")

        if not market_service:
            if logger:
                logger.log(
                    "crypto_market_service not available — "
                    "CoinsService NOT registered",
                    level="ERROR", tag="crypto_coins",
                )
            return

        if not db_service:
            if logger:
                logger.log(
                    "app_db_service not available — "
                    "CoinsService NOT registered",
                    level="ERROR", tag="crypto_coins",
                )
            return

        # --- 2. Create and register service -------------------
        try:
            self._service = CoinsService(
                market_service=market_service,
                db_service=db_service,
                logger=logger,
            )
            context.services.set(
                "crypto_coins_service", self._service
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"CoinsService init failed: {exc}",
                    level="ERROR", tag="crypto_coins",
                )
            self._service = None
            return

        if logger:
            logger.log(
                "crypto_coins_service registered",
                tag="crypto_coins",
            )
            logger.log(
                "crypto_coins module started "
                "(service only; UI in later tasks)",
                tag="crypto_coins",
            )

    async def stop(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")

        # CoinsService is stateless; nothing to close.

        if logger:
            logger.log(
                "crypto_coins module stopped",
                tag="crypto_coins",
            )
