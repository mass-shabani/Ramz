"""
Bank account repository.

Handles CRUD for the `bank_account` table. Bank accounts belong to a
contact (not directly to the user).
"""
from typing import Optional

from ._helpers import (
    db_insert,
    db_update,
    db_delete,
    result_ok,
    result_last_id,
)


class BankAccountRepository:

    TABLE = "bank_account"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_id(self, account_id: int) -> Optional[dict]:
        if not account_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"bank_account_id": int(account_id)},
        )

    async def list_by_contact(self, contact_id: int) -> list[dict]:
        if not contact_id:
            return []
        return await self._conn().find_many(
            self.TABLE,
            where={"contact_id": int(contact_id), "enabled": 1},
        )

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def create(
        self,
        contact_id: int,
        bank_id: int,
        account_number: str,
        account_name: str,
        iban: Optional[str] = None,
    ) -> Optional[int]:
        if not contact_id or not bank_id or not account_number or not account_name:
            return None
        result = await db_insert(self._conn(), self.TABLE, {
            "contact_id":     int(contact_id),
            "bank_id":        int(bank_id),
            "account_number": account_number,
            "account_name":   account_name,
            "iban":           iban,
            "enabled":        1,
        })
        return result_last_id(result)

    async def update(self, account_id: int, **fields) -> bool:
        if not account_id:
            return False
        allowed = {
            "bank_id", "account_number", "account_name", "iban",
        }
        values = {k: v for k, v in fields.items() if k in allowed}
        if not values:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"bank_account_id": int(account_id)},
            values=values,
        )
        return result_ok(result)

    async def delete(self, account_id: int) -> bool:
        if not account_id:
            return False
        result = await db_delete(
            self._conn(),
            self.TABLE,
            where={"bank_account_id": int(account_id)},
        )
        return result_ok(result)
