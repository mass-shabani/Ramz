"""
Form access repository.

Handles the `form_access` table — the many-to-many join between `role`
and `form` that also carries the `condition_id` describing *how* the
access is granted.

This table has a composite primary key (role_id, form_id) and is
typically queried by one of the two keys.
"""
from typing import Optional


class FormAccessRepository:

    TABLE = "form_access"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get(
        self, role_id, form_id: str
    ) -> Optional[dict]:
        if not role_id or not form_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"role_id": role_id, "form_id": form_id},
        )

    async def list_by_role(self, role_id) -> list[dict]:
        if not role_id:
            return []
        return await self._conn().find_many(
            self.TABLE,
            where={"role_id": role_id},
        )

    async def list_by_form(self, form_id: str) -> list[dict]:
        """
        Return all form_access rows referring to the given form.
        Used when checking which roles can access a specific form.
        """
        if not form_id:
            return []
        return await self._conn().find_many(
            self.TABLE,
            where={"form_id": form_id},
        )

    async def get_full_access(self, role_id) -> list[dict]:
        if not role_id:
            return []
        sql = """
            SELECT
                fa.role_id,
                fa.form_id,
                f.form_name,
                fa.condition_id,
                c.condition_name
            FROM form_access fa
            JOIN form         f ON f.form_id      = fa.form_id
            JOIN condition_of c ON c.condition_id = fa.condition_id
            WHERE fa.role_id = ?
        """
        return await self._conn().fetch_all(sql, (role_id,))

    async def get_full_access_one(
        self, role_id, form_id: str
    ) -> Optional[dict]:
        if not role_id or not form_id:
            return None
        sql = """
            SELECT
                fa.role_id,
                fa.form_id,
                f.form_name,
                fa.condition_id,
                c.condition_name
            FROM form_access fa
            JOIN form         f ON f.form_id      = fa.form_id
            JOIN condition_of c ON c.condition_id = fa.condition_id
            WHERE fa.role_id = ? AND fa.form_id = ?
            LIMIT 1
        """
        return await self._conn().fetch_one(sql, (role_id, form_id))

    async def create(
        self,
        role_id,
        form_id: str,
        condition_id,
    ) -> bool:
        if not role_id or not form_id or not condition_id:
            return False
        from ._helpers import db_insert, result_ok
        result = await db_insert(self._conn(), self.TABLE, {
            "role_id":      role_id,
            "form_id":      form_id,
            "condition_id": condition_id,
        })
        return result_ok(result)
