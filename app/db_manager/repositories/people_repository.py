"""
People repository.
"""
from typing import Optional

from ._helpers import (
    db_insert,
    db_update,
    result_ok,
    result_last_id,
)


class PeopleRepository:

    TABLE = "people"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_id(self, people_id: int) -> Optional[dict]:
        if not people_id:
            return None
        return await self._conn().find_one(
            self.TABLE, where={"people_id": int(people_id)}
        )

    async def get_by_contact_id(self, contact_id: int) -> Optional[dict]:
        if not contact_id:
            return None
        return await self._conn().find_one(
            self.TABLE, where={"contact_id": int(contact_id)}
        )

    async def get_by_national_code(
        self, national_code: str
    ) -> Optional[dict]:
        if not national_code:
            return None
        return await self._conn().find_one(
            self.TABLE, where={"national_code": national_code}
        )

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def create(
        self,
        contact_id: int,
        first_name: str,
        last_name: str,
        national_code: Optional[str] = None,
        birth_date: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> Optional[int]:
        if not contact_id or not first_name or not last_name:
            return None

        if gender not in (None, "male", "female", "other"):
            gender = None

        result = await db_insert(self._conn(), self.TABLE, {
            "contact_id":    int(contact_id),
            "first_name":    first_name,
            "last_name":     last_name,
            "national_code": national_code,
            "birth_date":    birth_date,
            "gender":        gender,
        })
        return result_last_id(result)

    async def update(self, people_id: int, **fields) -> bool:
        if not people_id:
            return False

        allowed = {
            "first_name", "last_name", "national_code",
            "birth_date", "gender",
        }
        values = {k: v for k, v in fields.items() if k in allowed}
        if not values:
            return False

        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"people_id": int(people_id)},
            values=values,
        )
        return result_ok(result)
