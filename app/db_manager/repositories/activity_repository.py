"""
Activity repository.

Handles the `user_activity_log` table and its lookup table
`activity_type`.

Design notes
------------
• The activity_type lookup is cached in memory with a long TTL because
  it changes very rarely. The cache is per-repository instance.

• log() is fail-safe: it catches every exception and returns False
  rather than raising. Logging must never break the calling operation.
"""
import time
from typing import Optional

from ..models.activity import Activity


class ActivityRepository:

    LOG_TABLE    = "user_activity_log"
    TYPE_TABLE   = "activity_type"

    # Cache TTL for activity_type lookups (seconds)
    TYPE_CACHE_TTL = 600.0

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

        # Cache: type_name -> (timestamp_monotonic, type_id)
        self._type_id_cache: dict[str, tuple[float, int]] = {}

    def _conn(self):
        return self._db.connection()

    def _now(self) -> float:
        return time.monotonic()

    def _log(self, message, level="INFO"):
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="database")
            except Exception:
                pass

    # ----------------------------------------------------------
    # Activity type lookup (cached)
    # ----------------------------------------------------------
    async def get_type_id(self, type_name: str) -> Optional[int]:
        """
        Return the activity_type_id for the given type_name, or None if
        the type does not exist. Result is cached for TYPE_CACHE_TTL.
        """
        if not type_name:
            return None

        cached = self._type_id_cache.get(type_name)
        if cached and (self._now() - cached[0]) < self.TYPE_CACHE_TTL:
            return cached[1]

        row = await self._conn().find_one(
            self.TYPE_TABLE,
            where={"type_name": type_name},
        )
        if not row:
            return None

        type_id = int(row["activity_type_id"])
        self._type_id_cache[type_name] = (self._now(), type_id)
        return type_id

    async def list_types(self) -> list[dict]:
        """
        Return every row from activity_type (id, name, description).
        """
        return await self._conn().find_many(self.TYPE_TABLE, where={})

    # ----------------------------------------------------------
    # Logging
    # ----------------------------------------------------------
    async def log(
        self,
        user_id: int,
        type_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Insert a row into user_activity_log.

        Never raises. Returns True on success, False on any failure.
        If the given type_name is not registered in activity_type, the
        call returns False without inserting.
        """
        if not user_id or not type_name:
            return False

        try:
            type_id = await self.get_type_id(type_name)
            if type_id is None:
                self._log(
                    f"Activity type '{type_name}' not found — skipping log",
                    level="WARNING",
                )
                return False

            await self._conn().insert(
                self.LOG_TABLE,
                {
                    "user_id":          int(user_id),
                    "activity_type_id": int(type_id),
                    "ip_address":       ip_address,
                    "user_agent":       user_agent,
                },
            )
            return True

        except Exception as exc:
            self._log(f"Failed to log activity: {exc}", level="ERROR")
            return False

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Activity]:
        """
        Return recent activities for a user, newest first, enriched with
        the type name.

        Parameters
        ----------
        user_id : int
        limit : int
            Maximum rows to return (default 20, capped at 200).
        offset : int
            Rows to skip (for pagination).
        """
        if not user_id:
            return []

        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))

        sql = """
            SELECT
                a.activity_id,
                a.user_id,
                a.ip_address,
                a.user_agent,
                a.action_time,
                t.type_name
            FROM user_activity_log a
            JOIN activity_type t ON t.activity_type_id = a.activity_type_id
            WHERE a.user_id = ?
            ORDER BY a.action_time DESC, a.activity_id DESC
            LIMIT ? OFFSET ?
        """
        rows = await self._conn().fetch_all(sql, (int(user_id), limit, offset))
        return [Activity.from_row(row) for row in rows or []]

    async def count_by_user(self, user_id: int) -> int:
        """Return the total number of activity rows for the user."""
        if not user_id:
            return 0
        row = await self._conn().fetch_one(
            "SELECT COUNT(*) AS c FROM user_activity_log WHERE user_id = ?",
            (int(user_id),),
        )
        return int(row["c"]) if row else 0

    # ----------------------------------------------------------
    # Cache management
    # ----------------------------------------------------------
    def invalidate_type_cache(self) -> None:
        """Clear the activity_type id cache."""
        self._type_id_cache.clear()
