"""
crypto_providers Module

Holds concrete crypto data providers and the encrypted per-user
credential store for those providers.

This module has NO page UI. It exposes:

    • `crypto_credentials_service` — encrypted API-key storage and
                                     retrieval for any provider.

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

Startup sequence (this task)
----------------------------
    start():
        1. Resolve encryption_api, app_db_service, core_config,
           app_dir from context.
        2. Instantiate MasterKeyManager and warm up the master key
           (load or create) — any I/O error surfaces here, not at
           first credential save.
        3. Instantiate CredentialRepository and CredentialService.
        4. Register `crypto_credentials_service` in context.services.

    If any prerequisite (encryption_api, app_db_service, app_dir,
    master key) is missing or fails to load, the service is NOT
    registered and an ERROR is logged. The module continues — no
    crash — matching the project's fail-soft convention.

Providers (TASK 78.4-78.7) and settings routes (TASK 78.8-78.9)
will be added in later tasks.
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
    """

    def __init__(self):
        self._key_manager = None
        self._credential_service = None

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
            logger.log(
                "crypto_providers module started "
                "(credentials service registered)",
                tag="crypto_providers",
            )

    async def stop(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")
        # No background tasks, no open connections to close here.
        # CredentialService holds no I/O resources; MasterKeyManager
        # caches the key in memory only.
        if logger:
            logger.log(
                "crypto_providers module stopped",
                tag="crypto_providers",
            )
