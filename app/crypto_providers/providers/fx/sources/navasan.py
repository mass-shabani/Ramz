"""
navasan — FX source for navasan.net (Iranian exchange-rate API).

STATUS: STUB. Not yet functional.

This file exists so that the factory in module.py can construct a
navasan source when configured, without crashing. `get_rates()`
returns an empty dict until the actual API integration is written.

To enable the real integration, the following must be implemented:

    1. Confirm the exact endpoint URL and response schema with
       navasan.net (or the chosen alternative — bonbast.com is a
       common alternative for Iranian FX).
    2. Add the HTTP call (httpx — already a project dependency).
    3. Parse the response into {currency_code: Decimal(rate_vs_RLS)}.
    4. Handle errors (timeout, HTTP 4xx/5xx, malformed JSON) by
       returning an empty dict — never raise.
    5. Respect navasan's rate limits (if any) via a rate limiter or
       a longer cache TTL in the provider configuration.

Config keys (already wired through module.py):

    "crypto_providers": {
      "fx": {
        "source": "navasan",
        "cache_ttl": 60.0,
        "sources": {
          "navasan": {
            "api_key": "<provided by navasan.net>",
            "timeout": 7.0
          }
        }
      }
    }

Until the implementation is complete, selecting `source = "navasan"`
in config produces a provider that registers successfully but
returns no rates — the aggregator will simply skip FX conversion.
"""
from decimal import Decimal

from .base import BaseFxSource


class NavasanFxSource(BaseFxSource):
    """
    Stub FX source for navasan.net.

    See module docstring for the implementation checklist.
    """

    def __init__(
        self,
        api_key: str = "",
        timeout: float = 7.0,
        logger=None,
    ):
        self._api_key = (api_key or "").strip()
        self._timeout = float(timeout)
        self._logger = logger
        self._not_implemented_logged = False

    async def get_rates(self) -> dict[str, Decimal]:
        if not self._not_implemented_logged:
            self._not_implemented_logged = True
            if self._logger:
                try:
                    self._logger.log(
                        "NavasanFxSource: STUB — no rates available. "
                        "Implement integration to enable real FX. "
                        "(This warning is logged once.)",
                        level="WARNING", tag="crypto_providers",
                    )
                except Exception:
                    pass
        return {}

    def __repr__(self) -> str:
        configured = "yes" if self._api_key else "no"
        return (
            f"NavasanFxSource(api_key_configured={configured}, "
            f"timeout={self._timeout}s)"
        )


__all__ = ["NavasanFxSource"]
