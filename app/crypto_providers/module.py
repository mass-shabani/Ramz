"""
crypto_providers Module

Holds concrete crypto data providers and the encrypted per-user
credential store for those providers.

This module has NO page UI. It exposes:

    • `crypto_credentials_service` — encrypted API-key storage and
                                     retrieval for any provider.
                                     (registered in TASK 78.3)

Internal structure:
    providers/          — one subfolder per provider (Nobitex, CoinGecko,
                          FX). Each implements BaseCryptoProvider from
                          crypto_market and registers itself under the
                          service key `crypto_provider_<name>`.
    repositories/       — DB access (crypto_credential table)
    templates/partials/ — Jinja partials for the account_setting
                          section (TASK 78.9)
    routes.py           — settings routes (TASK 78.8)
    services.py         — CredentialService (TASK 78.2)

Startup sequence (full, across the phase)
-----------------------------------------
1. TASK 78.1 (this task): skeleton only — module loads, logs, no
   services registered, no providers discovered by crypto_market yet.
2. TASK 78.2-78.3: CredentialService is registered.
3. TASK 78.4-78.7: Providers are instantiated and registered. Once
   the first provider registers, crypto_market's
   `ProviderRegistry.discover()` (fired from ON_ALL_MODULES_STARTED)
   will find it, and the poller will begin fetching real data when a
   UI session is active.
4. TASK 78.8-78.10: Settings UI for entering provider credentials.

Deployment notes
----------------
Enabling crypto_providers without crypto_market is rejected by
Massir's check_requirements (crypto_providers declares crypto_market
in `requires`). Enabling crypto_market without crypto_providers is
valid — the market module starts with zero providers, as observed in
phase 1 logs.
"""
from massir.core.interfaces import IModule, ModuleContext


class CryptoProvidersModule(IModule):
    """
    crypto_providers module — data providers + credentials.

    Provides (after TASK 78.3):
        crypto_credentials_service (CredentialService)
    """

    async def start(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")

        if logger:
            logger.log(
                "crypto_providers module starting…",
                tag="crypto_providers",
            )

        # Services, providers, and routes are added in later tasks.
        # See module docstring for the full sequence.

        if logger:
            logger.log(
                "crypto_providers module started "
                "(skeleton — no services yet)",
                tag="crypto_providers",
            )

    async def stop(self, context: ModuleContext) -> None:
        logger = context.services.get("core_logger")

        if logger:
            logger.log(
                "crypto_providers module stopped",
                tag="crypto_providers",
            )
