"""
Form repository.

Handles the `form` table. A "form" here is any checkable element in the
application: a page, a partial, a field, a button, an icon — anything
that access control may need to verify by name.

The `form_id` is a TEXT primary key chosen by the application, not an
auto-increment integer.
"""
from typing import Optional

from ._helpers import (
    db_insert,
    db_update,
    db_delete,
    result_ok,
)


class FormRepository:

    TABLE = "form"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_id(self, form_id: str) -> Optional[dict]:
        """Return the form row for the given form_id, or None."""
        if not form_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"form_id": form_id},
        )

    async def get_by_name(self, form_name: str) -> Optional[dict]:
        """Return the form row matching the given form_name, or None."""
        if not form_name:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"form_name": form_name},
        )

    async def list_enabled(self) -> list[dict]:
        """Return all enabled forms."""
        return await self._conn().find_many(
            self.TABLE,
            where={"enabled": 1},
        )

    async def list_all_with_grant_counts(self) -> list[dict]:
        """
        Return all forms (enabled + disabled), each enriched with
        `grants_count` = number of rows in form_access referencing it.
        Sorted by form_id ascending.
        """
        sql = """
            SELECT
                f.form_id,
                f.form_name,
                f.description,
                f.enabled,
                COUNT(fa.role_id) AS grants_count
            FROM form f
            LEFT JOIN form_access fa ON fa.form_id = f.form_id
            GROUP BY f.form_id, f.form_name, f.description, f.enabled
            ORDER BY f.form_id ASC
        """
        return await self._conn().fetch_all(sql) or []

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def create(
        self,
        form_id: str,
        form_name: str,
        description: str = "",
        enabled: bool = True,
    ) -> bool:
        """Create a form row. Returns True on success."""
        if not form_id or not form_name:
            return False
        result = await db_insert(self._conn(), self.TABLE, {
            "form_id":     form_id,
            "form_name":   form_name,
            "description": description,
            "enabled":     1 if enabled else 0,
        })
        return result_ok(result)

    async def update(
        self,
        form_id: str,
        form_name: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """Update a form. Only whitelisted fields. Returns True on success."""
        if not form_id:
            return False

        values = {}
        if form_name is not None:
            values["form_name"] = form_name
        if description is not None:
            values["description"] = description
        if enabled is not None:
            values["enabled"] = 1 if enabled else 0

        if not values:
            return False

        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"form_id": form_id},
            values=values,
        )
        return result_ok(result)

    async def delete(self, form_id: str) -> bool:
        """Delete a form row. Returns True on success."""
        if not form_id:
            return False
        result = await db_delete(
            self._conn(),
            self.TABLE,
            where={"form_id": form_id},
        )
        return result_ok(result)
