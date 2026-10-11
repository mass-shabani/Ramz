"""
Contact repository.
"""
from typing import Optional

from ._helpers import db_insert, result_last_id


class ContactRepository:

    TABLE = "contact"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    async def get_by_id(self, contact_id: int) -> Optional[dict]:
        if not contact_id:
            return None
        return await self._conn().find_one(
            self.TABLE, where={"contact_id": int(contact_id)}
        )

    async def create(self) -> Optional[int]:
        result = await db_insert(self._conn(), self.TABLE, {})
        return result_last_id(result)
