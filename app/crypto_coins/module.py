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
        component_service = context.services.get("component_service")

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

        # --- 2b. Register content scripts (TASK 79.5) -------------
        # content-container loads these per partial URL. Partial
        # HTML no longer contains <script src> (which would not
        # execute after innerHTML injection).
        if component_service and hasattr(
            component_service, "register_content_script"
        ):
            try:
                component_service.register_content_script(
                    "/crypto/coins/partials/list",
                    "/static/crypto_coins/js/coins_list.js",
                )
                component_service.register_content_script(
                    "/crypto/coins/partials/settings",
                    "/static/crypto_coins/js/coins_settings.js",
                )
                # Dashboard widget: register for the dashboard URL
                # so the widget's custom element is defined before
                # the extension HTML (added in TASK 79.7) is parsed.
                component_service.register_content_script(
                    "/panel/dashboard",
                    "/static/crypto_coins/js/top-coins-widget.js",
                )
                # Presence heartbeat — keeps crypto_market poller
                # alive while a coins partial is open. Registered
                # for both partial URLs; presence.js is idempotent
                # so double-loading across navigation is safe.
                component_service.register_content_script(
                    "/crypto/coins/partials/list",
                    "/static/crypto_coins/js/presence.js",
                )
                component_service.register_content_script(
                    "/crypto/coins/partials/settings",
                    "/static/crypto_coins/js/presence.js",
                )
                if logger:
                    logger.log(
                        "crypto_coins content scripts registered "
                        "(list, settings, top-coins-widget, presence)",
                        tag="crypto_coins",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"content script registration failed: {exc}",
                        level="WARNING", tag="crypto_coins",
                    )

        # --- 2c. Register UI extensions (TASK 79.7) ----------------
        # Sidebar items and dashboard widget are consumed by the
        # Phase 0 infrastructure (ramz-sidebar reads
        # window.__ramz.extensions['ui.sidebar.items']; dashboard-
        # content.html iterates ui_extensions['ui.dashboard.widgets']).
        if component_service and hasattr(
            component_service, "register_extension"
        ):
            try:
                coins_icon = (
                    '<svg viewBox="0 0 24 24" fill="none" '
                    'stroke="currentColor" stroke-width="1.9" '
                    'stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M12 2v20"/>'
                    '<path d="M17 6.5c0-1.9-2.2-3-5-3s-5 1.1-5 3 '
                    '2.2 2.7 5 3 5 1.1 5 3-2.2 3-5 3-5-1.1-5-3"/>'
                    '</svg>'
                )
                settings_icon = (
                    '<svg viewBox="0 0 24 24" fill="none" '
                    'stroke="currentColor" stroke-width="1.9" '
                    'stroke-linecap="round" stroke-linejoin="round">'
                    '<circle cx="12" cy="12" r="3"/>'
                    '<path d="M12 2v3M12 19v3M2 12h3M19 12h3'
                    'M4.9 4.9l2.1 2.1M17 17l2.1 2.1'
                    'M4.9 19.1l2.1-2.1M17 7l2.1-2.1"/>'
                    '</svg>'
                )

                component_service.register_extension(
                    "ui.sidebar.items",
                    {
                        "label":    "Crypto Coins",
                        "endpoint": "/crypto/coins/partials/list",
                        "icon":     coins_icon,
                        "order":    100,
                        "group":    "Crypto",
                    },
                    "crypto.coins.view",
                    "crypto_coins",
                )
                component_service.register_extension(
                    "ui.sidebar.items",
                    {
                        "label":    "Coin Settings",
                        "endpoint": "/crypto/coins/partials/settings",
                        "icon":     settings_icon,
                        "order":    110,
                        "group":    "Crypto",
                    },
                    "crypto.coins.favorite",
                    "crypto_coins",
                )
                component_service.register_extension(
                    "ui.dashboard.widgets",
                    {
                        "html":  (
                            '<top-coins-widget '
                            'endpoint="/crypto/coins/api/summary">'
                            '</top-coins-widget>'
                        ),
                        "order": 10,
                    },
                    "crypto.coins.view",
                    "crypto_coins",
                )
                if logger:
                    logger.log(
                        "crypto_coins UI extensions registered "
                        "(2 sidebar items, 1 dashboard widget)",
                        tag="crypto_coins",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"UI extension registration failed: {exc}",
                        level="WARNING", tag="crypto_coins",
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

        # --- 3b. Register static directory -------------------
        # Serves /static/crypto_coins/* from app/crypto_coins/static/*.
        # Required for coins_settings.js (external <script src> that
        # executes when injected via innerHTML; inline scripts do not).
        if (
            template_service
            and hasattr(
                template_service, "register_module_static_directory"
            )
        ):
            try:
                static_dir = str(
                    Path(__file__).parent / "static"
                )
                template_service.register_module_static_directory(
                    "crypto_coins", static_dir
                )
                if logger:
                    logger.log(
                        "static directory registered at "
                        "/static/crypto_coins",
                        tag="crypto_coins",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"static directory registration failed: "
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
