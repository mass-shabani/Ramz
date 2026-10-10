"""
Phone repository.

Handles the `phone` table. Multiple phones can belong to one contact.
The `user` table stores a `phone_id` pointing to the primary phone.
"""
from typing import Optional


class PhoneRepository:

    TABLE = "phone"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_id(self, phone_id: int) -> Optional[dict]:
        if not phone_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"phone_id": int(phone_id)},
        )

    async def get_by_number(self, number: str) -> Optional[dict]:
        if not number:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"phone_number": number},
        )

    async def list_by_contact(self, contact_id: int) -> list[dict]:
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
        phone_number: str,
        phone_type: str = "mobile",
        is_verified: bool = False,
    ) -> Optional[int]:
        """
        Create a phone row and return its phone_id.

        phone_type must be one of: mobile, home, work, fax.
        """
        if not contact_id or not phone_number:
            return None

        allowed = {"mobile", "home", "work", "fax"}
        if phone_type not in allowed:
            phone_type = "mobile"

        result = await self._conn().insert(
            self.TABLE,
            {
                "contact_id":   int(contact_id),
                "phone_number": phone_number,
                "phone_type":   phone_type,
                "is_verified":  1 if is_verified else 0,
            },
        )
        return _extract_last_insert_id(result)

    async def update_number(
        self, phone_id: int, new_number: str
    ) -> bool:
        """Change the phone number. Resets verification."""
        if not phone_id or not new_number:
            return False
        result = await self._conn().update(
            self.TABLE,
            where={"phone_id": int(phone_id)},
            values={"phone_number": new_number, "is_verified": 0},
        )
        return _update_ok(result)

    async def set_verified(
        self, phone_id: int, verified: bool = True
    ) -> bool:
        if not phone_id:
            return False
        result = await self._conn().update(
            self.TABLE,
            where={"phone_id": int(phone_id)},
            values={"is_verified": 1 if verified else 0},
        )
        return _update_ok(result)

    async def delete(self, phone_id: int) -> bool:
        if not phone_id:
            return False
        result = await self._conn().delete(
            self.TABLE,
            where={"phone_id": int(phone_id)},
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
