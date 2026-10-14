"""
Bank repository.

Handles the `bank` lookup table (list of banks). Banks are pre-seeded
by the administrator and are used to populate the bank selector in
the account settings page.
"""
from typing import Optional


class BankRepository:

    TABLE = "bank"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    async def get_by_id(self, bank_id: int) -> Optional[dict]:
        if not bank_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"bank_id": int(bank_id)},
        )

    async def get_by_name(self, bank_name: str) -> Optional[dict]:
        if not bank_name:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"bank_name": bank_name},
        )

    async def list_enabled(self) -> list[dict]:
        """Return all enabled banks, sorted by name."""
        rows = await self._conn().find_many(
            self.TABLE,
            where={"enabled": 1},
        )
        # Sort in Python — SQLite collation differences across platforms
        return sorted(rows, key=lambda r: (r.get("bank_name") or "").lower())
