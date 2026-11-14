"""
mock — static FX rates read from configuration.

This source is the default in `crypto_providers.fx.source` because it
allows end-to-end testing without any external API. Configure rates
under `crypto_providers.fx.sources.mock.*`:

    "crypto_providers": {
      "fx": {
        "sources": {
          "mock": {
            "usd_rls": "900000",
            "eur_rls": "1050000"
          }
        }
      }
    }

If a rate is missing from config, the default (see DEFAULTS below)
is used. The source is deterministic — repeated calls return the
same rates. Cache invalidation is unnecessary; the FX provider still
applies its TTL because it doesn't know the source is static.
"""
from decimal import Decimal, InvalidOperation

from .base import BaseFxSource


# Defaults applied when config omits a rate. Values are placeholder
# and should be overridden in production configuration.
DEFAULTS: dict[str, str] = {
    "USD": "900000",
    "EUR": "1000000",
}


class MockFxSource(BaseFxSource):
    """
    Deterministic FX source backed by an in-memory dict.

    See module docstring for config layout.
    """

    def __init__(self, rates: dict | None = None, logger=None):
        self._logger = logger
        self._rates: dict[str, Decimal] = self._parse_rates(
            rates if rates is not None else DEFAULTS
        )

    async def get_rates(self) -> dict[str, Decimal]:
        # Return a copy so the caller cannot mutate internal state.
        return dict(self._rates)

    # ----------------------------------------------------------
    # Internal
    # ----------------------------------------------------------
    @staticmethod
    def _parse_rates(raw: dict) -> dict[str, Decimal]:
        """
        Convert raw config values (strings or numbers) to Decimal,
        skipping any entries that cannot be parsed or are non-positive.
        """
        result: dict[str, Decimal] = {}
        for currency, value in raw.items():
            if not isinstance(currency, str):
                continue
            code = currency.strip().upper()
            if not code or code == "RLS":
                continue
            try:
                d = Decimal(str(value))
            except (InvalidOperation, ValueError, TypeError):
                continue
            if not d.is_finite() or d <= 0:
                continue
            result[code] = d
        return result

    def __repr__(self) -> str:
        return (
            f"MockFxSource(currencies="
            f"{sorted(self._rates.keys())})"
        )


__all__ = ["MockFxSource", "DEFAULTS"]
