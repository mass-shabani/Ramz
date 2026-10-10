"""
Condition repository.

Handles the `condition_of` table. A "condition" is a label attached to
a form_access entry. The application interprets what the label means
(e.g. "low", "medium", "high", a number, or free-form text).
"""
from typing import Optional


class ConditionRepository:

    TABLE = "condition_of"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_id(self, condition_id: int) -> Optional[dict]:
        """Return the condition row for the given condition_id, or None."""
        if not condition_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"condition_id": int(condition_id)},
        )

    async def get_by_name(self, condition_name: str) -> Optional[dict]:
        """Return the condition row matching the given name, or None."""
        if not condition_name:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"condition_name": condition_name},
        )

    async def list_enabled(self) -> list[dict]:
        """Return all enabled conditions."""
        return await self._conn().find_many(
            self.TABLE,
            where={"enabled": 1},
        )
