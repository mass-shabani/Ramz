"""
presence — track active UI sessions for the crypto_market poller.

Purpose
-------
The poller (market_data.poller) should only call provider APIs while
at least one browser session is actively viewing crypto data. This
module tracks that state.

A "session" is identified by the `session_id` cookie already used by
Ramz auth. Each heartbeat from a UI partial tells the registry:

    • "I am still here"          → refresh the session timestamp
    • "These UIs are open in me" → merge the declared "kinds"

A "kind" is a free-form string naming a live-data consumer. Current
convention:

    "coins"   — crypto_coins partial (coin list page)
    "charts"  — crypto_charts partial (chart page)

New kinds can be introduced without changing this registry — it
treats them as opaque strings.

Thread safety
-------------
All methods are synchronous and do NOT await inside their critical
sections. Because Massir runs on a single asyncio event loop, no
coroutine can preempt another mid-execution. No lock is needed.

The only correctness constraint is Python's dict-mutation-during-
iteration rule: `_prune` collects expired keys into a list first,
then removes them, avoiding the "dictionary changed size during
iteration" RuntimeError.

This design assumes single-threaded asyncio. If a future change
introduces threads (e.g. run_in_executor with shared state), this
module must be revisited.

TTL and heartbeat interval
--------------------------
The TTL defaults to 90 seconds. The client heartbeat interval should
be at least 2× shorter (typically 30s) so a single missed heartbeat
does not drop the session. If a browser crashes without sending
`leave()`, the session is pruned after TTL expires.
"""
import time
from typing import Optional


DEFAULT_TTL = 90.0  # seconds


class PresenceRegistry:
    """
    In-memory tracker of active UI sessions.

    See module docstring for lifecycle and design rationale.
    """

    def __init__(self, ttl: float = DEFAULT_TTL, logger=None):
        self._ttl = float(ttl)
        self._logger = logger
        # session_id → monotonic timestamp of last heartbeat
        self._entries: dict[str, float] = {}
        # session_id → set of kinds declared by that session
        self._kinds: dict[str, set[str]] = {}

    # ----------------------------------------------------------
    # Mutations
    # ----------------------------------------------------------
    def heartbeat(
        self,
        session_id: str,
        kinds: Optional[list[str]] = None,
    ) -> None:
        """
        Record a heartbeat for `session_id`.

        If `kinds` is provided, its members are merged into the
        session's existing kinds set. Repeated heartbeats with the
        same kinds are idempotent. A heartbeat from a second tab that
        declares a different kind adds that kind to the same session.

        Args:
            session_id: Stable session identifier (auth cookie value).
                Empty/None is silently ignored — callers may pass
                unauthenticated session IDs without special-casing.
            kinds: Optional list of kind names to merge.
        """
        if not session_id:
            return

        self._entries[session_id] = time.monotonic()

        if kinds:
            existing = self._kinds.setdefault(session_id, set())
            existing.update(kinds)

    def leave(
        self,
        session_id: str,
        kinds: Optional[list[str]] = None,
    ) -> None:
        """
        Remove a session, or specific kinds from it.

        Args:
            session_id: Session identifier to remove.
            kinds:
                • None or empty list → remove the entire session
                  (entry + all kinds).
                • Non-empty list → remove only those kinds. If no
                  kinds remain, the session entry itself is removed.

        Empty/None session_id is silently ignored.
        """
        if not session_id:
            return

        if not kinds:
            self._entries.pop(session_id, None)
            self._kinds.pop(session_id, None)
            return

        current = self._kinds.get(session_id)
        if not current:
            # No kinds recorded for this session; nothing to do.
            return

        current -= set(kinds)
        if not current:
            # All kinds removed → drop the session entirely.
            self._entries.pop(session_id, None)
            self._kinds.pop(session_id, None)

    def clear(self) -> None:
        """Remove every tracked session. Used for shutdown/testing."""
        self._entries.clear()
        self._kinds.clear()

    # ----------------------------------------------------------
    # Queries
    # ----------------------------------------------------------
    def active_count(self) -> int:
        """
        Number of sessions that have heartbeated within TTL.

        Triggers pruning of expired entries first, so the returned
        count is always accurate as of the call.
        """
        self._prune()
        return len(self._entries)

    def active_kinds(self) -> set[str]:
        """
        Union of all kinds declared by active sessions.

        Example: if two sessions are active, one declaring
        {"coins"} and another declaring {"coins", "charts"},
        returns {"coins", "charts"}.
        """
        self._prune()
        result: set[str] = set()
        for kinds in self._kinds.values():
            result |= kinds
        return result

    def has_kind(self, kind: str) -> bool:
        """
        True if at least one active session declares `kind`.

        Used by the poller to decide whether to call a specific
        provider capability (e.g. "should I fetch klines?").
        """
        if not kind:
            return False
        self._prune()
        for kinds in self._kinds.values():
            if kind in kinds:
                return True
        return False

    def session_count(self, kind: str) -> int:
        """Number of active sessions that declare `kind`."""
        if not kind:
            return 0
        self._prune()
        return sum(1 for kinds in self._kinds.values() if kind in kinds)

    def ttl(self) -> float:
        """Current TTL in seconds."""
        return self._ttl

    def info(self) -> dict:
        """
        Serializable summary for logging and /status endpoints.

        Never returns session IDs or any user-identifying data.
        """
        self._prune()
        return {
            "active_sessions": len(self._entries),
            "active_kinds":    sorted(self.active_kinds()),
            "ttl_seconds":     self._ttl,
        }

    # ----------------------------------------------------------
    # Internal
    # ----------------------------------------------------------
    def _prune(self) -> int:
        """
        Remove sessions whose heartbeat is older than TTL.

        Returns the number of sessions removed.

        Iterates over a snapshot (`list(self._entries.items())`) to
        avoid RuntimeError if the caller happens to trigger a
        heartbeat from within the same call stack (defensive; not
        expected in normal operation).
        """
        now = time.monotonic()
        expired = [
            sid for sid, ts in list(self._entries.items())
            if now - ts > self._ttl
        ]
        for sid in expired:
            self._entries.pop(sid, None)
            self._kinds.pop(sid, None)
        return len(expired)

    def _log(self, message: str, level: str = "INFO") -> None:
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="crypto_market")
            except Exception:
                pass

    def __repr__(self) -> str:
        return (
            f"PresenceRegistry("
            f"sessions={len(self._entries)}, "
            f"ttl={self._ttl}s)"
        )
