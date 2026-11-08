"""
crypto_market Module

Core crypto market data layer for the Ramz application.

This module has NO UI. It exposes:

    • `crypto_market_service`           — public API for consumers
                                          (CryptoMarketService)
    • `crypto_symbol_map_repository`    — symbol map for providers
                                          (used by crypto_providers)

Internal structure:
    market_data/       — provider interface, registry, aggregator,
                         presence, poller, types
    market_service/    — public API (CryptoMarketService)
    repositories/      — DB access (symbol map, future price history)

Startup sequence
----------------
1. `start()`:
   • Instantiate ProviderRegistry, PresenceRegistry, Aggregator,
     MarketPoller, SymbolMapRepository.
   • Create CryptoMarketService.
   • Register both `crypto_market_service` and
     `crypto_symbol_map_repository` in `context.services`.
   • Register a hook on ON_ALL_MODULES_STARTED that:
       a. Calls `registry.discover(context.services)` — this is the
          earliest point at which provider modules are guaranteed
          to have registered their services.
       b. Starts the poller loop.
   
   Why not do (a) and (b) directly in start()?
   ─────────────────────────────────────────
   In Massir, module execution order is determined by run-order groups
   and topological sort over `requires`. crypto_market does NOT (and
   must not) declare `crypto_providers` in its `requires` — otherwise
   disabling providers would disable the market module. Therefore
   `crypto_providers` may start either before or after crypto_market.
   Deferring discovery to ON_ALL_MODULES_STARTED eliminates the
   ordering ambiguity entirely.

2. `stop()`:
   • Stop the poller loop.
   • (context.services is being torn down by Massir; no manual
     cleanup needed.)

Deployment
----------
Enabling crypto_market without crypto_providers is valid: the module
starts, discovery finds zero providers, the poller starts but does
nothing (no presence, no providers), and any consumer that calls the
service gets empty results. This is by design.
"""
from massir.core.interfaces import IModule, ModuleContext
from massir.core.hook_types import SystemHook

from .market_data.registry import ProviderRegistry
from .market_data.presence import PresenceRegistry
from .market_data.aggregator import Aggregator
from .market_data.poller import MarketPoller
from .market_service.api import CryptoMarketService
from .repositories.symbol_map_repository import SymbolMapRepository
from .routes import register_routes


class CryptoMarketModule(IModule):
    """
    crypto_market module — data layer only, no UI.

    Provides:
        crypto_market_service           (CryptoMarketService)
        crypto_symbol_map_repository    (SymbolMapRepository)
    """

    def __init__(self):
        # Core components (created in start(), released in stop())
        self._registry:    ProviderRegistry          = None
        self._presence:    PresenceRegistry          = None
        self._aggregator:  Aggregator                = None
        self._poller:      MarketPoller              = None
        self._service:     CryptoMarketService       = None
        self._symbol_repo: SymbolMapRepository       = None

        # Guard against stop() arriving before ON_ALL_MODULES_STARTED
        # fires (defensive; not expected in normal Massir flow).
        self._shutting_down: bool = False

    # ----------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------
    async def start(self, context: ModuleContext) -> None:
        logger     = context.services.get("core_logger")
        db_service = context.services.get("database_service")
        app        = context.get_app()

        if logger:
            logger.log(
                "crypto_market module starting…", tag="crypto_market"
            )

        if not db_service:
            if logger:
                logger.log(
                    "database_service not available — "
                    "crypto_market cannot start",
                    level="ERROR", tag="crypto_market",
                )
            return

        if not app:
            if logger:
                logger.log(
                    "app reference not available — crypto_market "
                    "cannot register hooks and will not start",
                    level="ERROR", tag="crypto_market",
                )
            return

        # --- Instantiate core components --------------------
        self._registry   = ProviderRegistry(logger=logger)
        self._presence   = PresenceRegistry(logger=logger)
        self._aggregator = Aggregator(logger=logger)
        self._symbol_repo = SymbolMapRepository(db_service, logger=logger)

        # --- Register symbol repo (for crypto_providers) ----
        context.services.set(
            "crypto_symbol_map_repository", self._symbol_repo
        )

        # --- Create poller ---------------------------------
        self._poller = MarketPoller(
            registry=self._registry,
            aggregator=self._aggregator,
            presence=self._presence,
            logger=logger,
        )

        # --- Create and register public service ------------
        self._service = CryptoMarketService(
            registry=self._registry,
            presence=self._presence,
            aggregator=self._aggregator,
            poller=self._poller,
            logger=logger,
        )
        context.services.set("crypto_market_service", self._service)

        # --- Register routes (JSON API) --------------------
        http_api = context.services.get("http_api")
        if http_api:
            try:
                register_routes(
                    http_api=http_api,
                    service=self._service,
                    db_service=db_service,
                    logger=logger,
                )
                if logger:
                    logger.log(
                        "crypto_market routes registered "
                        "(presence heartbeat + leave)",
                        tag="crypto_market",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"crypto_market route registration failed: {exc}",
                        level="ERROR", tag="crypto_market",
                    )
        else:
            if logger:
                logger.log(
                    "http_api not available — crypto_market routes "
                    "NOT registered. Service is still usable by "
                    "direct consumers.",
                    level="WARNING", tag="crypto_market",
                )

        # --- Defer discovery + poller start ----------------
        async def on_all_modules_started() -> None:
            if self._shutting_down:
                return

            try:
                count = self._registry.discover(context.services)
                if logger:
                    logger.log(
                        f"Provider discovery complete "
                        f"({count} provider(s) registered)",
                        tag="crypto_market",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"Provider discovery failed: {exc}",
                        level="ERROR", tag="crypto_market",
                    )
            finally:
                # Start the poller regardless — with zero providers it
                # is a no-op loop; with providers it begins fetching
                # as soon as presence > 0.
                if self._poller is not None and not self._shutting_down:
                    try:
                        await self._poller.start()
                    except Exception as exc:
                        if logger:
                            logger.log(
                                f"Poller start failed: {exc}",
                                level="ERROR", tag="crypto_market",
                            )

        app.register_hook(
            SystemHook.ON_ALL_MODULES_STARTED, on_all_modules_started
        )

        if logger:
            route_status = "routes registered" if http_api else "no routes"
            logger.log(
                f"crypto_market module started "
                f"({route_status}; discovery deferred to "
                f"ON_ALL_MODULES_STARTED)",
                tag="crypto_market",
            )

    async def stop(self, context: ModuleContext) -> None:
        self._shutting_down = True

        logger = context.services.get("core_logger")

        if self._poller is not None:
            try:
                await self._poller.stop()
            except Exception as exc:
                if logger:
                    logger.log(
                        f"Poller stop failed: {exc}",
                        level="ERROR", tag="crypto_market",
                    )

        if logger:
            logger.log(
                "crypto_market module stopped", tag="crypto_market"
            )
