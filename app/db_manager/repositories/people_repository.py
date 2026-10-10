"""
People repository.

Handles the `people` table (personal information such as first name,
last name, birth date, gender, national code).

This repository only covers single-table operations. Any workflow that
needs to combine `people` with other tables must do so in workflows/.
"""
from typing import Optional


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
        """
        Return the people row for the given people_id, or None.
        """
        if not people_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"people_id": int(people_id)},
        )

    async def get_by_contact_id(self, contact_id: int) -> Optional[dict]:
        """
        Return the people row linked to the given contact_id, or None.

        A contact has at most one people row in the current schema.
        """
        if not contact_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"contact_id": int(contact_id)},
        )

    async def get_by_national_code(self, national_code: str) -> Optional[dict]:
        """
        Return the people row matching the national code, or None.
        """
        if not national_code:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"national_code": national_code},
        )
