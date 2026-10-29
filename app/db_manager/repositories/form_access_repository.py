"""
Form access repository.

Handles the `form_access` table — the many-to-many join between `role`
and `form` that carries a numeric `level`.

`level` semantics:
    0 = Closed (no access)
    ≥1 = Open; higher values indicate privileged levels

This table has a composite primary key (role_id, form_id).
"""
from typing import Optional

from ._helpers import db_insert, db_update, db_delete, result_ok


class FormAccessRepository:

    TABLE = "form_access"
    FORM_TABLE = "form"

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
        if not form_id:
            return []
        return await self._conn().find_many(
            self.TABLE,
            where={"form_id": form_id},
        )

    async def list_all_with_details(
        self,
        role_filter: str = "",
        form_filter: str = "",
        query: str = "",
    ) -> list[dict]:
        """
        Return all grants, enriched with role_name, form_name,
        role_enabled, and form_enabled.
        """
        where_parts = []
        params = []

        if role_filter:
            where_parts.append("fa.role_id = ?")
            params.append(role_filter)
        if form_filter:
            where_parts.append("fa.form_id = ?")
            params.append(form_filter)
        if query:
            like = f"%{query}%"
            where_parts.append(
                "(fa.role_id LIKE ? OR fa.form_id LIKE ? OR f.form_name LIKE ?)"
            )
            params.extend([like, like, like])

        where_sql = ""
        if where_parts:
            where_sql = "WHERE " + " AND ".join(where_parts)

        sql = f"""
            SELECT
                fa.role_id,
                fa.form_id,
                fa.level,
                r.role_name,
                r.enabled   AS role_enabled,
                f.form_name,
                f.enabled   AS form_enabled
            FROM form_access fa
            LEFT JOIN role r ON r.role_id = fa.role_id
            LEFT JOIN form f ON f.form_id = fa.form_id
            {where_sql}
            ORDER BY fa.role_id ASC, fa.form_id ASC
        """
        return await self._conn().fetch_all(sql, tuple(params)) or []

    async def list_role_form_summary(self, role_id: str) -> list[dict]:
        """
        Return all forms, each annotated with the level (if any) the
        given role has for it. Used by the "View by role" panel.

        Each item:
            {form_id, form_name, form_enabled, level}
            level is None if no grant exists for this role/form.

        Implementation note: this uses two simple queries and merges in
        Python instead of a LEFT JOIN with a parameter in the ON clause.
        SQLite drivers occasionally fail to bind `?` correctly in
        `JOIN ... ON` — this approach is driver-agnostic and safe.
        """
        if not role_id:
            return []

        forms = await self._conn().find_many(self.FORM_TABLE, where={})
        forms = sorted(forms or [], key=lambda r: r.get("form_id", ""))

        grants = await self._conn().find_many(
            self.TABLE, where={"role_id": role_id}
        )
        level_map = {}
        for g in grants or []:
            fid = g.get("form_id")
            if fid:
                level_map[fid] = int(g.get("level", 0))

        result = []
        for f in forms:
            fid = f.get("form_id")
            result.append({
                "form_id":      fid,
                "form_name":    f.get("form_name") or "",
                "form_enabled": bool(f.get("enabled")),
                "level":        level_map.get(fid),
            })
        return result

    async def get_full_access(self, role_id) -> list[dict]:
        if not role_id:
            return []
        sql = """
            SELECT
                fa.role_id,
                fa.form_id,
                fa.level,
                f.form_name
            FROM form_access fa
            JOIN form f ON f.form_id = fa.form_id
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
                fa.level,
                f.form_name
            FROM form_access fa
            JOIN form f ON f.form_id = fa.form_id
            WHERE fa.role_id = ? AND fa.form_id = ?
            LIMIT 1
        """
        return await self._conn().fetch_one(sql, (role_id, form_id))

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def create(
        self,
        role_id,
        form_id: str,
        level: int = 1,
    ) -> bool:
        if not role_id or not form_id:
            return False
        result = await db_insert(self._conn(), self.TABLE, {
            "role_id": role_id,
            "form_id": form_id,
            "level":   int(level),
        })
        return result_ok(result)

    async def update_level(
        self, role_id, form_id: str, new_level: int
    ) -> bool:
        """Update the level of an existing grant."""
        if not role_id or not form_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"role_id": role_id, "form_id": form_id},
            values={"level": int(new_level)},
        )
        return result_ok(result)

    async def delete(self, role_id, form_id: str) -> bool:
        """Delete a grant."""
        if not role_id or not form_id:
            return False
        result = await db_delete(
            self._conn(),
            self.TABLE,
            where={"role_id": role_id, "form_id": form_id},
        )
        return result_ok(result)
