"""
Form repository.

Handles the `form` table. A "form" here is any checkable element in the
application: a page, a partial, a field, a button, an icon — anything
that access control may need to verify by name.

The `form_id` is a TEXT primary key chosen by the application, not an
auto-increment integer.
"""
from typing import Optional


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
