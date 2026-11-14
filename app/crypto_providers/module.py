"""
crypto_providers Module

Holds concrete crypto data providers and the encrypted per-user
credential store for those providers.

This module has NO page UI. It exposes:

    • `crypto_credentials_service` — encrypted API-key storage and
                                     retrieval for any provider.
    • `crypto_provider_nobitex`    — Nobitex public market data
                                     provider (implements
                                     BaseCryptoProvider).

Internal structure:
    providers/          — one subfolder per provider (Nobitex, CoinGecko,
                          FX). Each implements BaseCryptoProvider from
                          crypto_market and registers itself under the
                          service key `crypto_provider_<name>`.
    repositories/       — DB access (crypto_credential table)
    key_manager.py      — master encryption key management
    services.py         — CredentialService
    templates/partials/ — Jinja partials for the account_setting
                          section (TASK 78.9)
    routes.py           — settings routes (TASK 78.8)

Startup sequence
----------------
    start():
        1. Resolve encryption_api, app_db_service, core_config,
           app_dir from context.
        2. Instantiate MasterKeyManager and warm up the master key.
        3. Instantiate CredentialRepository and CredentialService;
           register `crypto_credentials_service`.
        4. Instantiate Nobitex provider and register it under
           `crypto_provider_nobitex`. Imported lazily so a missing
           `httpx` dependency degrades to "provider not registered"
           instead of failing the whole module load.

    Each step is fail-soft: a failure logs an ERROR and skips only
    that step, without crashing the module. This matches the
    project's convention and keeps the app bootable when a
    dependency is missing.

Provider discovery
------------------
crypto_market's ProviderRegistry runs its discovery on
ON_ALL_MODULES_STARTED, scanning `crypto_provider_*` services. Once
this module has registered `crypto_provider_nobitex`, the market
poller begins fetching when a UI session is active (or when
`refresh_now(force=True)` is called via the coins endpoint).

Deployment notes
----------------
Enabling crypto_providers without crypto_market is rejected by
Massir's check_requirements (crypto_providers declares
crypto_symbol_map_repository, provided by crypto_market). Enabling
crypto_market without crypto_providers is valid — discovery finds
zero providers, as observed in phase 1 logs.
"""
from massir.core.interfaces import IModule, ModuleContext

from .key_manager import MasterKeyManager
from .repositories.credential_repository import CredentialRepository
from .services import CredentialService


class CryptoProvidersModule(IModule):
    """
    crypto_providers module — data providers + credentials.

    Provides:
        crypto_credentials_service (CredentialService)
        crypto_provider_nobitex (NobitexProvider)
        crypto_provider_coingecko (CoinGeckoProvider)
        crypto_provider_fx (FxProvider)
    """

    def __init__(self):
        self._key_manager = None
        self._credential_service = None
        self._nobitex_client = None
        self._coingecko_client = None
        self._fx_provider = None

    async def start(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")

        if logger:
            logger.log(
                "crypto_providers module starting…",
                tag="crypto_providers",
            )

        # --- 1. Resolve prerequisites -------------------------
        encryption_api = context.services.get("encryption_api")
        db_service     = context.services.get("app_db_service")
        config         = context.services.get("core_config")
        app_dir        = context.app_dir

        if not encryption_api:
            if logger:
                logger.log(
                    "encryption_api not available — credentials "
                    "service NOT registered",
                    level="ERROR", tag="crypto_providers",
                )
            return

        if not db_service:
            if logger:
                logger.log(
                    "app_db_service not available — credentials "
                    "service NOT registered",
                    level="ERROR", tag="crypto_providers",
                )
            return

        if not app_dir:
            if logger:
                logger.log(
                    "app_dir not available — credentials service "
                    "NOT registered",
                    level="ERROR", tag="crypto_providers",
                )
            return

        # --- 2. Master key manager (warm up) ------------------
        try:
            self._key_manager = MasterKeyManager(
                app_dir=app_dir, config=config, logger=logger,
            )
            _ = self._key_manager.get_key()
        except Exception as exc:
            if logger:
                logger.log(
                    f"MasterKeyManager init failed: {exc} — "
                    f"credentials service NOT registered",
                    level="ERROR", tag="crypto_providers",
                )
            self._key_manager = None
            return

        # --- 3. Repository + service --------------------------
        try:
            repo = CredentialRepository(db_service, logger=logger)
            self._credential_service = CredentialService(
                repository=repo,
                encryption_api=encryption_api,
                key_manager=self._key_manager,
                logger=logger,
            )
            context.services.set(
                "crypto_credentials_service",
                self._credential_service,
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"CredentialService init failed: {exc}",
                    level="ERROR", tag="crypto_providers",
                )
            self._credential_service = None
            return

        if logger:
            logger.log(
                "crypto_credentials_service registered",
                tag="crypto_providers",
            )

        # --- 4. Nobitex provider ------------------------------
        # Lazy import so missing `httpx` (or any provider-side
        # import error) degrades to "provider not registered"
        # rather than failing the whole module import.
        try:
            from .providers.nobitex.client import NobitexClient
            from .providers.nobitex.provider import NobitexProvider
            from .providers.nobitex.rate_limiter import RateLimiter
        except ImportError as exc:
            if logger:
                logger.log(
                    f"Nobitex provider import failed (httpx "
                    f"installed?): {exc} — provider NOT registered",
                    level="ERROR", tag="crypto_providers",
                )
        else:
            try:
                rate_limiter = RateLimiter(
                    max_requests=20,
                    window_seconds=60.0,
                    logger=logger,
                    name="nobitex_stats",
                )
                nobitex_client = NobitexClient(
                    rate_limiter=rate_limiter,
                    logger=logger,
                )
                await nobitex_client.start()
                self._nobitex_client = nobitex_client

                nobitex_provider = NobitexProvider(
                    client=nobitex_client,
                    logger=logger,
                )
                context.services.set(
                    "crypto_provider_nobitex", nobitex_provider
                )

                if logger:
                    logger.log(
                        f"Nobitex provider registered "
                        f"(capabilities="
                        f"{sorted(nobitex_provider.capabilities)}, "
                        f"quotes="
                        f"{sorted(nobitex_provider.supported_quotes)})",
                        tag="crypto_providers",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"Nobitex provider init failed: {exc} — "
                        f"provider NOT registered",
                        level="ERROR", tag="crypto_providers",
                    )
                # Close the client if it was started
                if self._nobitex_client is not None:
                    try:
                        await self._nobitex_client.stop()
                    except Exception:
                        pass
                    self._nobitex_client = None

        # --- 5. CoinGecko provider ----------------------------
        try:
            from .providers.coingecko.client import CoinGeckoClient
            from .providers.coingecko.provider import CoinGeckoProvider
            from .providers.coingecko.rate_limiter import (
                RateLimiter as CGRateLimiter,
            )
        except ImportError as exc:
            if logger:
                logger.log(
                    f"CoinGecko provider import failed (httpx "
                    f"installed?): {exc} — provider NOT registered",
                    level="ERROR", tag="crypto_providers",
                )
        else:
            try:
                cg_rate_limiter = CGRateLimiter(
                    max_requests=30,
                    window_seconds=60.0,
                    logger=logger,
                    name="coingecko_markets",
                )
                coingecko_client = CoinGeckoClient(
                    rate_limiter=cg_rate_limiter,
                    logger=logger,
                )
                await coingecko_client.start()
                self._coingecko_client = coingecko_client

                coingecko_provider = CoinGeckoProvider(
                    client=coingecko_client,
                    logger=logger,
                )
                context.services.set(
                    "crypto_provider_coingecko", coingecko_provider
                )

                if logger:
                    logger.log(
                        f"CoinGecko provider registered "
                        f"(capabilities="
                        f"{sorted(coingecko_provider.capabilities)}, "
                        f"quotes="
                        f"{sorted(coingecko_provider.supported_quotes)})",
                        tag="crypto_providers",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"CoinGecko provider init failed: {exc} — "
                        f"provider NOT registered",
                        level="ERROR", tag="crypto_providers",
                    )
                if self._coingecko_client is not None:
                    try:
                        await self._coingecko_client.stop()
                    except Exception:
                        pass
                    self._coingecko_client = None

        # --- 6. FX provider -----------------------------------
        try:
            from .providers.fx.provider import FxProvider
            from .providers.fx.sources.mock import MockFxSource
            from .providers.fx.sources.navasan import NavasanFxSource
        except ImportError as exc:
            if logger:
                logger.log(
                    f"FX provider import failed: {exc} — "
                    f"provider NOT registered",
                    level="ERROR", tag="crypto_providers",
                )
        else:
            try:
                source_name = "mock"
                cache_ttl = 60.0
                if config:
                    source_name = str(
                        config.get(
                            "crypto_providers.fx.source", "mock"
                        ) or "mock"
                    ).strip().lower()
                    try:
                        cache_ttl = float(config.get(
                            "crypto_providers.fx.cache_ttl", 60.0
                        ))
                    except (TypeError, ValueError):
                        cache_ttl = 60.0

                if source_name == "navasan":
                    api_key = ""
                    nav_timeout = 7.0
                    if config:
                        api_key = str(config.get(
                            "crypto_providers.fx.sources.navasan.api_key",
                            "",
                        ) or "")
                        try:
                            nav_timeout = float(config.get(
                                "crypto_providers.fx.sources.navasan.timeout",
                                7.0,
                            ))
                        except (TypeError, ValueError):
                            nav_timeout = 7.0
                    fx_source = NavasanFxSource(
                        api_key=api_key,
                        timeout=nav_timeout,
                        logger=logger,
                    )
                else:
                    # Default: mock
                    mock_rates: dict = {}
                    if config:
                        for ccy, conf_key in (
                            ("USD", "crypto_providers.fx.sources.mock.usd_rls"),
                            ("EUR", "crypto_providers.fx.sources.mock.eur_rls"),
                        ):
                            value = config.get(conf_key, None)
                            if value is not None:
                                mock_rates[ccy] = value
                    fx_source = MockFxSource(
                        rates=mock_rates or None,
                        logger=logger,
                    )

                fx_provider = FxProvider(
                    source=fx_source,
                    logger=logger,
                    cache_ttl=cache_ttl,
                )
                await fx_provider.start()
                self._fx_provider = fx_provider

                context.services.set(
                    "crypto_provider_fx", fx_provider
                )

                if logger:
                    logger.log(
                        f"FX provider registered "
                        f"(source={source_name!r}, "
                        f"cache_ttl={cache_ttl}s, "
                        f"quotes="
                        f"{sorted(fx_provider.supported_quotes)})",
                        tag="crypto_providers",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"FX provider init failed: {exc} — "
                        f"provider NOT registered",
                        level="ERROR", tag="crypto_providers",
                    )
                self._fx_provider = None

        if logger:
            logger.log(
                "crypto_providers module started "
                "(credentials + nobitex + coingecko + fx providers)",
                tag="crypto_providers",
            )

    async def stop(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")

        # Close both provider HTTP clients. The poller may still be
        # trying to fetch through them for a brief window (Massir
        # stops crypto_providers before crypto_market); any resulting
        # exception is caught by the poller and treated as a failed
        # cycle — harmless at shutdown.
        if self._nobitex_client is not None:
            try:
                await self._nobitex_client.stop()
            except Exception as exc:
                if logger:
                    logger.log(
                        f"Nobitex client stop failed: {exc}",
                        level="WARNING", tag="crypto_providers",
                    )
            self._nobitex_client = None

        if self._coingecko_client is not None:
            try:
                await self._coingecko_client.stop()
            except Exception as exc:
                if logger:
                    logger.log(
                        f"CoinGecko client stop failed: {exc}",
                        level="WARNING", tag="crypto_providers",
                    )
            self._coingecko_client = None

        # FX provider: stop its source (no-op for mock; future
        # navasan will close its httpx client here).
        if self._fx_provider is not None:
            try:
                await self._fx_provider.stop()
            except Exception as exc:
                if logger:
                    logger.log(
                        f"FX provider stop failed: {exc}",
                        level="WARNING", tag="crypto_providers",
                    )
            self._fx_provider = None

        # CredentialService holds no I/O resources; MasterKeyManager
        # caches the key in memory only. Nothing else to close.

        if logger:
            logger.log(
                "crypto_providers module stopped",
                tag="crypto_providers",
            )
