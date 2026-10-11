"""
Address repository.
"""
from typing import Optional

from ._helpers import (
    db_insert,
    db_update,
    db_delete,
    result_ok,
    result_last_id,
)


class AddressRepository:

    TABLE = "post_address"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    async def get_by_id(self, address_id: int) -> Optional[dict]:
        if not address_id:
            return None
        return await self._conn().find_one(
            self.TABLE, where={"address_id": int(address_id)}
        )

    async def list_by_contact(self, contact_id: int) -> list[dict]:
        if not contact_id:
            return []
        return await self._conn().find_many(
            self.TABLE, where={"contact_id": int(contact_id)}
        )

    async def get_primary(self, contact_id: int) -> Optional[dict]:
        if not contact_id:
            return None
        addresses = await self.list_by_contact(contact_id)
        if not addresses:
            return None
        for addr in addresses:
            if (addr.get("address_type") or "").lower() == "home":
                return addr
        return addresses[0]

    async def create(
        self,
        contact_id: int,
        address_line1: str,
        address_line2: Optional[str] = None,
        city: Optional[str] = None,
        state_province: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: str = "Iran",
        address_type: str = "home",
    ) -> Optional[int]:
        if not contact_id or not address_line1:
            return None

        allowed = {"home", "work", "billing", "shipping"}
        if address_type not in allowed:
            address_type = "home"

        result = await db_insert(self._conn(), self.TABLE, {
            "contact_id":     int(contact_id),
            "address_line1":  address_line1,
            "address_line2":  address_line2,
            "city":           city,
            "state_province": state_province,
            "postal_code":    postal_code,
            "country":        country,
            "address_type":   address_type,
        })
        return result_last_id(result)

    async def update(self, address_id: int, **fields) -> bool:
        if not address_id:
            return False

        allowed = {
            "address_line1", "address_line2", "city",
            "state_province", "postal_code", "country", "address_type",
        }
        values = {k: v for k, v in fields.items() if k in allowed}
        if not values:
            return False

        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"address_id": int(address_id)},
            values=values,
        )
        return result_ok(result)

    async def delete(self, address_id: int) -> bool:
        if not address_id:
            return False
        result = await db_delete(
            self._conn(),
            self.TABLE,
            where={"address_id": int(address_id)},
        )
        return result_ok(result)
