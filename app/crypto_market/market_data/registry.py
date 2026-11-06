"""
registry — provider discovery for the crypto_market data layer.

Scans `context.services` for provider instances registered by provider-
owning modules (currently only crypto_providers, but the design is
generic). Discovery runs once, typically at ON_ALL_MODULES_STARTED,
after all modules have registered their services.

Service key convention
----------------------
A provider module must register its instance under a key of the form:

    crypto_provider_<name>

where `<name>` matches the provider instance's `.name` property.
Examples:

    crypto_provider_nobitex
    crypto_provider_coingecko
    crypto_provider_fx

The prefix is configurable but defaults to "crypto_provider_".

Discovery mechanism
-------------------
`ProviderRegistry.discover()` uses the public `ModuleRegistry.find()`
API added in MASSIR-NO-1:

    matching = services.find(prefix="crypto_provider_")

`find()` returns a dict mapping key → instance, filtered by prefix.
The registry then validates each candidate (type check, non-empty
name, no duplicates) and stores the survivors by provider name.

No fallback is present: if `services.find` is missing, discovery
logs an ERROR and returns 0. This is intentional — a missing
`find()` means Massir is out of date, and failing loudly is better
than silently using a fragile private-attribute scan.
"""
import time
from typing import Optional

from .interfaces import BaseCryptoProvider


DEFAULT_PREFIX = "crypto_provider_"


class ProviderRegistry:
    """
    Holds discovered provider instances and indexes them by name,
    capability, and supported quotes.

    Lifecycle
    ---------
    1. Instantiated by crypto_market (see market_service/api.py) with
       an optional logger.
    2. `discover(services)` is called once at ON_ALL_MODULES_STARTED.
    3. Query methods (get / all / by_capability / by_quote) are used
       by the aggregator and the poller during operation.
    4. `refresh(services)` may be called again if a re-scan is needed
       (e.g. developer hot-reload). It is a no-op if the discovered
       set is unchanged.

    Thread safety
    -------------
    Discovery is sync and runs once at startup, before any request
    is served. Query methods return snapshots (lists) and are safe to
    call from async code without locking. Refresh is not expected
    during operation and should not be called concurrently.
    """

    def __init__(self, logger=None):
        self._logger = logger
        self._providers: dict[str, BaseCryptoProvider] = {}
        self._discovered_at: Optional[float] = None

    # ----------------------------------------------------------
    # Discovery
    # ----------------------------------------------------------
    def discover(
        self, services, prefix: str = DEFAULT_PREFIX
    ) -> int:
        """
        Scan `services` for provider instances registered under `prefix`.

        Uses the public `ModuleRegistry.find(prefix=...)` API. For each
        matching entry, performs three validations:

            1. The instance must be a BaseCryptoProvider.
            2. The instance must have a non-empty `.name`.
            3. The name must not collide with an already-registered
               provider (first registration wins).

        Non-conforming entries are logged and skipped — they do not
        abort discovery. This makes the registry resilient to unrelated
        services that happen to share the prefix.

        Returns
        -------
        int
            Number of providers successfully discovered.

        Side effects
        ------------
        Replaces the internal provider map. Providers registered via a
        previous `discover()` call are removed. To accumulate, use
        `refresh()` (which delegates here after a scan).
        """
        self._providers.clear()

        # --- Enumerate via the public API -----------------------
        try:
            matching: dict = services.find(prefix=prefix)
        except AttributeError:
            self._log(
                "services.find() is not available. Ensure Massir is "
                "up to date (MASSIR-NO-1). Discovery aborted.",
                level="ERROR",
            )
            return 0
        except Exception as exc:
            self._log(
                f"services.find(prefix='{prefix}') raised: {exc}. "
                f"Discovery aborted.",
                level="ERROR",
            )
            return 0

        if not isinstance(matching, dict):
            self._log(
                f"services.find returned unexpected type "
                f"{type(matching).__name__}; expected dict. "
                f"Discovery aborted.",
                level="ERROR",
            )
            return 0

        # --- Validate and index each candidate ------------------
        count = 0
        for key, instance in matching.items():
            if not isinstance(instance, BaseCryptoProvider):
                self._log(
                    f"Service '{key}' matches '{prefix}*' but is not "
                    f"a BaseCryptoProvider (got {type(instance).__name__}); "
                    f"skipping",
                    level="WARNING",
                )
                continue

            name = getattr(instance, "name", None)
            if not name:
                self._log(
                    f"Provider '{key}' has empty .name; skipping",
                    level="WARNING",
                )
                continue

            if name in self._providers:
                self._log(
                    f"Duplicate provider name '{name}' "
                    f"(key '{key}' ignored); keeping first registration",
                    level="WARNING",
                )
                continue

            self._providers[name] = instance
            count += 1

            self._log(
                f"Discovered provider '{name}' "
                f"(capabilities={sorted(instance.capabilities)}, "
                f"quotes={sorted(instance.supported_quotes)})"
            )

        self._discovered_at = time.monotonic()

        if count == 0:
            self._log(
                f"Provider discovery found no providers under "
                f"prefix '{prefix}'",
                level="WARNING",
            )
        else:
            self._log(f"Discovered {count} provider(s)")

        return count

    def refresh(
        self, services, prefix: str = DEFAULT_PREFIX
    ) -> int:
        """
        Re-run discovery. Semantically identical to `discover()`, kept
        as a separate method for call-site clarity in hot-reload paths.
        """
        return self.discover(services, prefix=prefix)

    def clear(self) -> None:
        """Drop all discovered providers and reset the timestamp."""
        self._providers.clear()
        self._discovered_at = None

    # ----------------------------------------------------------
    # Queries
    # ----------------------------------------------------------
    def get(self, name: str) -> Optional[BaseCryptoProvider]:
        """Return the provider registered under `name`, or None."""
        if not name:
            return None
        return self._providers.get(name)

    def all(self) -> list[BaseCryptoProvider]:
        """Return all providers (snapshot list)."""
        return list(self._providers.values())

    def by_capability(self, capability: str) -> list[BaseCryptoProvider]:
        """
        Return all providers that advertise `capability`.

        `capability` is one of CAP_COINS / CAP_KLINES / CAP_ORDERBOOK
        (see interfaces.py).
        """
        if not capability:
            return []
        return [
            p for p in self._providers.values()
            if capability in p.capabilities
        ]

    def by_quote(self, quote: str) -> list[BaseCryptoProvider]:
        """
        Return all providers that support quoting against `quote`
        (e.g. "USDT", "RLS", "USD").
        """
        if not quote:
            return []
        return [
            p for p in self._providers.values()
            if quote in p.supported_quotes
        ]

    def count(self) -> int:
        """Number of currently-registered providers."""
        return len(self._providers)

    def is_empty(self) -> bool:
        """True if no providers have been discovered."""
        return not self._providers

    def info(self) -> dict:
        """
        Return a serializable summary of the registry state.

        Intended for logging and /status endpoints. Never returns
        provider instances themselves.
        """
        return {
            "provider_count": len(self._providers),
            "providers": [
                {
                    "name":         p.name,
                    "capabilities": sorted(p.capabilities),
                    "quotes":       sorted(p.supported_quotes),
                }
                for p in self._providers.values()
            ],
            "discovered_at": self._discovered_at,
        }

    # ----------------------------------------------------------
    # Internal
    # ----------------------------------------------------------
    def _log(self, message: str, level: str = "INFO") -> None:
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="crypto_market")
            except Exception:
                pass

    def __repr__(self) -> str:
        names = sorted(self._providers.keys())
        return f"ProviderRegistry(providers={names})"
