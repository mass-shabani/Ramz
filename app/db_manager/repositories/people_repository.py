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
        """
        Create a new people row and return its people_id.

        Parameters
        ----------
        contact_id : int
            Must reference an existing contact row.
        first_name, last_name : str
            Required.
        national_code : str, optional
            Must be unique if provided.
        birth_date : str, optional
            ISO format "YYYY-MM-DD".
        gender : str, optional
            One of: male, female, other.

        Returns
        -------
        int or None
            The new people_id on success, None on failure.
        """
        if not contact_id or not first_name or not last_name:
            return None

        if gender not in (None, "male", "female", "other"):
            gender = None

        result = await self._conn().insert(
            self.TABLE,
            {
                "contact_id":    int(contact_id),
                "first_name":    first_name,
                "last_name":     last_name,
                "national_code": national_code,
                "birth_date":    birth_date,
                "gender":        gender,
            },
        )
        return _extract_last_insert_id(result)

    async def update(self, people_id: int, **fields) -> bool:
        """
        Update people fields. Only whitelisted columns are accepted
        to prevent accidental column injection.

        Returns True if at least one row was updated.
        """
        if not people_id:
            return False

        allowed = {
            "first_name", "last_name", "national_code",
            "birth_date", "gender",
        }
        values = {k: v for k, v in fields.items() if k in allowed}
        if not values:
            return False

        result = await self._conn().update(
            self.TABLE,
            where={"people_id": int(people_id)},
            values=values,
        )
        return _update_ok(result)


# --------------------------------------------------------------
# Helper
# --------------------------------------------------------------
def _extract_last_insert_id(result) -> Optional[int]:
    """Extract last_insert_id from framework's insert() return value."""
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
    """Interpret framework's update() return value."""
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
