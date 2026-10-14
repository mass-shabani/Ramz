"""
Phone repository.
"""
from typing import Optional

from ._helpers import (
    db_insert,
    db_update,
    db_delete,
    result_ok,
    result_last_id,
)


class PhoneRepository:

    TABLE = "phone"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    async def get_by_id(self, phone_id: int) -> Optional[dict]:
        if not phone_id:
            return None
        return await self._conn().find_one(
            self.TABLE, where={"phone_id": int(phone_id)}
        )

    async def get_by_number(self, number: str) -> Optional[dict]:
        if not number:
            return None
        return await self._conn().find_one(
            self.TABLE, where={"phone_number": number}
        )

    async def list_by_contact(self, contact_id: int) -> list[dict]:
        if not contact_id:
            return []
        return await self._conn().find_many(
            self.TABLE, where={"contact_id": int(contact_id)}
        )

    async def create(
        self,
        contact_id: int,
        phone_number: str,
        phone_type_id: int = 1,
        is_verified: bool = False,
    ) -> Optional[int]:
        if not contact_id or not phone_number:
            return None

        result = await db_insert(self._conn(), self.TABLE, {
            "contact_id":    int(contact_id),
            "phone_number":  phone_number,
            "phone_type_id": int(phone_type_id) if phone_type_id else 1,
            "is_verified":   1 if is_verified else 0,
        })
        return result_last_id(result)

    async def update_number(
        self, phone_id: int, new_number: str
    ) -> bool:
        if not phone_id or not new_number:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"phone_id": int(phone_id)},
            values={"phone_number": new_number, "is_verified": 0},
        )
        return result_ok(result)

    async def set_verified(
        self, phone_id: int, verified: bool = True
    ) -> bool:
        if not phone_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"phone_id": int(phone_id)},
            values={"is_verified": 1 if verified else 0},
        )
        return result_ok(result)

    async def delete(self, phone_id: int) -> bool:
        if not phone_id:
            return False
        result = await db_delete(
            self._conn(),
            self.TABLE,
            where={"phone_id": int(phone_id)},
        )
        return result_ok(result)

    async def list_by_contact_with_type(self, contact_id: int) -> list[dict]:
        """
        Return phones for the contact, each enriched with `type_name`
        from the phone_type lookup table.
        """
        if not contact_id:
            return []
        sql = """
            SELECT p.*, pt.type_name
            FROM phone p
            JOIN phone_type pt ON pt.phone_type_id = p.phone_type_id
            WHERE p.contact_id = ?
            ORDER BY p.phone_id ASC
        """
        return await self._conn().fetch_all(sql, (int(contact_id),))
