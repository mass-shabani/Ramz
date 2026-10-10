"""
Contact repository.

Handles the `contact` table. A contact is a hub row that links a
person to their contact information (emails, phones, addresses,
bank accounts).

The contact row itself carries no data — only its `contact_id` is
significant. Everything else lives in satellite tables.
"""
from typing import Optional


class ContactRepository:

    TABLE = "contact"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_id(self, contact_id: int) -> Optional[dict]:
        """Return the contact row for the given contact_id, or None."""
        if not contact_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"contact_id": int(contact_id)},
        )

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def create(self) -> Optional[int]:
        """
        Insert a new contact row and return its contact_id.

        Returns None on failure.
        """
        result = await self._conn().insert(self.TABLE, {})
        contact_id = _extract_last_insert_id(result)
        if contact_id is None:
            return None
        return contact_id


# --------------------------------------------------------------
# Helper
# --------------------------------------------------------------
def _extract_last_insert_id(result) -> Optional[int]:
    """
    Extract the last inserted row id from the framework's insert()
    return value.

    Some versions return QueryResult, some return an int directly.
    """
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
