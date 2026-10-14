"""
Address type repository.

Handles the `address_type` lookup table.
"""
from typing import Optional


class AddressTypeRepository:

    TABLE = "address_type"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    async def get_by_id(self, type_id: int) -> Optional[dict]:
        if not type_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"address_type_id": int(type_id)},
        )

    async def get_by_name(self, type_name: str) -> Optional[dict]:
        if not type_name:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"type_name": type_name},
        )

    async def list_enabled(self) -> list[dict]:
        rows = await self._conn().find_many(
            self.TABLE,
            where={"enabled": 1},
        )
        return sorted(rows, key=lambda r: r.get("address_type_id", 0))
