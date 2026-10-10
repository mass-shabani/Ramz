"""
Email repository.

Handles the `email` table. Multiple emails can belong to one contact
(e.g. personal and work). The `user` table stores a `email_id` pointing
to whichever email is the primary one.
"""
from typing import Optional


class EmailRepository:

    TABLE = "email"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_id(self, email_id: int) -> Optional[dict]:
        """Return the email row for the given email_id, or None."""
        if not email_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"email_id": int(email_id)},
        )

    async def get_by_address(self, address: str) -> Optional[dict]:
        """Return the email row matching the address, or None."""
        if not address:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"email_address": address},
        )

    async def list_by_contact(self, contact_id: int) -> list[dict]:
        """Return all emails belonging to a contact."""
        if not contact_id:
            return []
        return await self._conn().find_many(
            self.TABLE,
            where={"contact_id": int(contact_id)},
        )

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def create(
        self,
        contact_id: int,
        email_address: str,
        is_verified: bool = False,
    ) -> Optional[int]:
        """
        Create a new email row and return its email_id.

        Returns None on failure.
        """
        if not contact_id or not email_address:
            return None

        result = await self._conn().insert(
            self.TABLE,
            {
                "contact_id":    int(contact_id),
                "email_address": email_address,
                "is_verified":   1 if is_verified else 0,
            },
        )
        return _extract_last_insert_id(result)

    async def update_address(
        self, email_id: int, new_address: str
    ) -> bool:
        """Change the email address. Resets verification to 0."""
        if not email_id or not new_address:
            return False
        result = await self._conn().update(
            self.TABLE,
            where={"email_id": int(email_id)},
            values={"email_address": new_address, "is_verified": 0},
        )
        return _update_ok(result)

    async def set_verified(
        self, email_id: int, verified: bool = True
    ) -> bool:
        """Mark the email as verified (or not)."""
        if not email_id:
            return False
        result = await self._conn().update(
            self.TABLE,
            where={"email_id": int(email_id)},
            values={"is_verified": 1 if verified else 0},
        )
        return _update_ok(result)

    async def delete(self, email_id: int) -> bool:
        """Delete an email row."""
        if not email_id:
            return False
        result = await self._conn().delete(
            self.TABLE,
            where={"email_id": int(email_id)},
        )
        return _update_ok(result)


# --------------------------------------------------------------
# Helpers
# --------------------------------------------------------------
def _extract_last_insert_id(result) -> Optional[int]:
    if result is None:
        return None
    if isinstance(result, int):
        return result
    for attr in ("last_insert_id", "lastrowid", "last_row_id"):
        if hasattr(result, attr):
            try:
                return int(getattr(result, attr))
            except (TypeError, ValueError):
                pass
    return None


def _update_ok(result) -> bool:
    if result is None:
        return False
    if isinstance(result, int):
        return result > 0
    for attr in ("affected_rows", "rowcount", "rows_affected"):
        if hasattr(result, attr):
            try:
                return int(getattr(result, attr)) > 0
            except (TypeError, ValueError):
                pass
    return True
