"""
crypto_coins Module

Crypto coins page module. Provides:

    • CoinsService (JSON API wrapper over crypto_market_service).
    • /crypto/coins/partials/list — HTML shell for the coin list
      (consumed by user_panel's content-container).
    • /crypto/coins/api/list — JSON for <ramz-table>.

Later tasks add:
    • coins_settings partial + endpoints (TASK 79.4)
    • favorite toggle (TASK 79.5)
    • dashboard widget (TASK 79.6)
    • sidebar/dashboard extensions (TASK 79.7)
    • presence heartbeat (TASK 79.8)

Internal structure:
    services.py         — CoinsService
    repositories/       — UserPreferenceRepository
    templates/partials/ — coins_list.html (+ coins_settings.html later)
    routes.py           — JSON + HTML endpoints

Startup sequence
----------------
    start():
        1. Resolve crypto_market_service, app_db_service,
           http_api, template_service from context.
        2. Instantiate CoinsService + UserPreferenceRepository.
        3. Register `crypto_coins_service` in context.services.
        4. Register templates directory.
        5. Register routes.

    Each step is fail-soft: a missing prerequisite logs an ERROR
    and skips only that step, keeping the rest of the module load
    healthy.
"""
from pathlib import Path

from massir.core.interfaces import IModule, ModuleContext

from .repositories import UserPreferenceRepository
from .services import CoinsService


class CryptoCoinsModule(IModule):
    """
    crypto_coins module — coin list page + dashboard widget.

    Provides:
        crypto_coins_service (CoinsService)
    """

    def __init__(self):
        self._service = None
        self._preference_repo = None

    async def start(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")

        if logger:
            logger.log(
                "crypto_coins module starting…",
                tag="crypto_coins",
            )

        # --- 1. Resolve prerequisites -------------------------
        market_service    = context.services.get("crypto_market_service")
        db_service        = context.services.get("app_db_service")
        http_api          = context.services.get("http_api")
        template_service  = context.services.get("template_service")

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

        # --- 2. Create service + repository -------------------
        try:
            self._preference_repo = UserPreferenceRepository(
                db_service, module_name="coins", logger=logger
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"UserPreferenceRepository init failed: {exc}",
                    level="ERROR", tag="crypto_coins",
                )
            return

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

        # --- 3. Register templates directory ------------------
        if template_service:
            try:
                templates_dir = str(
                    Path(__file__).parent / "templates"
                )
                template_service.register_template_directory(
                    templates_dir, "crypto_coins"
                )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"templates directory registration failed: "
                        f"{exc}",
                        level="WARNING", tag="crypto_coins",
                    )

        # --- 4. Register routes -------------------------------
        if http_api:
            try:
                from .routes import register_routes
                register_routes(
                    http_api=http_api,
                    coins_service=self._service,
                    preference_repo=self._preference_repo,
                    db_service=db_service,
                    template_service=template_service,
                    logger=logger,
                )
                if logger:
                    logger.log(
                        "crypto_coins routes registered "
                        "(api/list, partials/list, api/settings, "
                        "api/settings/save, partials/settings)",
                        tag="crypto_coins",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"route registration failed: {exc}",
                        level="ERROR", tag="crypto_coins",
                    )
        else:
            if logger:
                logger.log(
                    "http_api not available — routes NOT registered",
                    level="WARNING", tag="crypto_coins",
                )

        if logger:
            logger.log(
                "crypto_coins module started "
                "(service + routes; UI extension in TASK 79.7)",
                tag="crypto_coins",
            )

    async def stop(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")

        # CoinsService and UserPreferenceRepository are stateless.
        # No I/O resources to close.

        if logger:
            logger.log(
                "crypto_coins module stopped",
                tag="crypto_coins",
            )
