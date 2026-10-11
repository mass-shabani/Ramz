"""
Email repository.
"""
from typing import Optional

from ._helpers import (
    db_insert,
    db_update,
    db_delete,
    result_ok,
    result_last_id,
)


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
        if not email_id:
            return None
        return await self._conn().find_one(
            self.TABLE, where={"email_id": int(email_id)}
        )

    async def get_by_address(self, address: str) -> Optional[dict]:
        if not address:
            return None
        return await self._conn().find_one(
            self.TABLE, where={"email_address": address}
        )

    async def list_by_contact(self, contact_id: int) -> list[dict]:
        if not contact_id:
            return []
        return await self._conn().find_many(
            self.TABLE, where={"contact_id": int(contact_id)}
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
        if not contact_id or not email_address:
            return None

        result = await db_insert(self._conn(), self.TABLE, {
            "contact_id":    int(contact_id),
            "email_address": email_address,
            "is_verified":   1 if is_verified else 0,
        })
        return result_last_id(result)

    async def update_address(
        self, email_id: int, new_address: str
    ) -> bool:
        if not email_id or not new_address:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"email_id": int(email_id)},
            values={"email_address": new_address, "is_verified": 0},
        )
        return result_ok(result)

    async def set_verified(
        self, email_id: int, verified: bool = True
    ) -> bool:
        if not email_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"email_id": int(email_id)},
            values={"is_verified": 1 if verified else 0},
        )
        return result_ok(result)

    async def delete(self, email_id: int) -> bool:
        if not email_id:
            return False
        result = await db_delete(
            self._conn(),
            self.TABLE,
            where={"email_id": int(email_id)},
        )
        return result_ok(result)
