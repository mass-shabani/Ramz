"""
Role repository.

Handles the `role` table (list of roles in the system, e.g. admin,
manager, user, guest).
"""
from typing import Optional

from ._helpers import db_insert, db_update, db_delete, result_ok


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

    async def list_all_with_grant_counts(self) -> list[dict]:
        """
        Return all roles (enabled + disabled), each enriched with
        `grants_count` = number of form_access rows referencing it,
        `rank` (numeric hierarchy), and `lock` flag.
        Sorted by role_id ascending.
        """
        sql = """
            SELECT
                r.role_id,
                r.role_name,
                r.description,
                r.rank,
                r.enabled,
                r.lock,
                COUNT(fa.form_id) AS grants_count
            FROM role r
            LEFT JOIN form_access fa ON fa.role_id = r.role_id
            GROUP BY r.role_id, r.role_name, r.description, r.rank, r.enabled, r.lock
            ORDER BY r.role_id ASC
        """
        return await self._conn().fetch_all(sql) or []

    async def count_users_with_role(self, role_id: str) -> int:
        """Return the number of users currently assigned this role."""
        if not role_id:
            return 0
        row = await self._conn().fetch_one(
            "SELECT COUNT(*) AS c FROM user WHERE role_id = ?",
            (role_id,),
        )
        return int(row["c"]) if row else 0

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def create(
        self,
        role_id: str,
        role_name: str,
        description: str = "",
        rank: int = 0,
        enabled: bool = True,
    ) -> bool:
        """Insert a new role. Returns True on success."""
        if not role_id or not role_name:
            return False
        result = await db_insert(self._conn(), self.TABLE, {
            "role_id":     role_id,
            "role_name":   role_name,
            "description": description,
            "rank":        int(rank),
            "enabled":     1 if enabled else 0,
        })
        return result_ok(result)

    async def update(
        self,
        role_id: str,
        role_name: Optional[str] = None,
        description: Optional[str] = None,
        rank: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """Update whitelisted role fields. Returns True on success."""
        if not role_id:
            return False

        values = {}
        if role_name is not None:
            values["role_name"] = role_name
        if description is not None:
            values["description"] = description
        if rank is not None:
            values["rank"] = int(rank)
        if enabled is not None:
            values["enabled"] = 1 if enabled else 0

        if not values:
            return False

        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"role_id": role_id},
            values=values,
        )
        return result_ok(result)

    async def delete(self, role_id: str) -> bool:
        """Delete a role. Returns True on success."""
        if not role_id:
            return False
        result = await db_delete(
            self._conn(),
            self.TABLE,
            where={"role_id": role_id},
        )
        return result_ok(result)

    async def set_lock(self, role_id: str, locked: bool) -> bool:
        """Set the `lock` flag on a role. Returns True on success."""
        if not role_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"role_id": role_id},
            values={"lock": 1 if locked else 0},
        )
        return result_ok(result)

    async def set_enabled(self, role_id: str, enabled: bool) -> bool:
        """Set the `enabled` flag on a role. Returns True on success."""
        if not role_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"role_id": role_id},
            values={"enabled": 1 if enabled else 0},
        )
        return result_ok(result)
