"""
base — abstract interface for FX sources.
"""
from abc import ABC, abstractmethod
from decimal import Decimal


class BaseFxSource(ABC):
    """
    Abstract FX rate source.

    Implementations must be safe to call concurrently. They must NOT
    raise on transient failures: return an empty dict instead. The
    provider treats an empty dict as "no fresh rates available" and
    falls back to its cache if any.
    """

    @abstractmethod
    async def get_rates(self) -> dict[str, Decimal]:
        """
        Return exchange rates vs RLS.

        Shape:
            {"USD": Decimal("900000"), "EUR": Decimal("1050000"), ...}
        meaning 1 USD = 900,000 RLS, 1 EUR = 1,050,000 RLS, etc.

        RLS itself is NOT included as a key (its rate vs RLS is 1 by
        definition and would be meaningless to report).

        Returns an empty dict on any error. Never raises.
        """

    async def start(self) -> None:
        """Optional lifecycle: open connections, warm up caches."""
        return None

    async def stop(self) -> None:
        """Optional lifecycle: close connections, release resources."""
        return None


__all__ = ["BaseFxSource"]
