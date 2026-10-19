"""
Role repository.

Handles the `role` table (list of roles in the system, e.g. admin,
manager, user, guest).
"""
from typing import Optional


class RoleRepository:

    TABLE = "role"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_id(self, role_id) -> Optional[dict]:
        if not role_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"role_id": role_id},
        )

    async def get_by_name(self, role_name: str) -> Optional[dict]:
        """Return the role row matching the given role_name, or None."""
        if not role_name:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"role_name": role_name},
        )

    async def list_enabled(self) -> list[dict]:
        rows = await self._conn().find_many(
            self.TABLE,
            where={"enabled": 1},
        )
        return sorted(rows, key=lambda r: r.get("role_id", ""))
