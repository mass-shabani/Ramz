"""
Bank card repository.

Handles CRUD for the `bank_card` table. Cards belong to a bank account.
"""
from typing import Optional

from ._helpers import (
    db_insert,
    db_update,
    db_delete,
    result_ok,
    result_last_id,
)


class BankCardRepository:

    TABLE = "bank_card"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    async def get_by_id(self, card_id: int) -> Optional[dict]:
        if not card_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"bank_card_id": int(card_id)},
        )

    async def list_by_account(self, account_id: int) -> list[dict]:
        """
        Return ALL cards for the account, including disabled ones.
        """
        if not account_id:
            return []
        return await self._conn().find_many(
            self.TABLE,
            where={"bank_account_id": int(account_id)},
        )

    async def list_by_contact(self, contact_id: int) -> list[dict]:
        """
        Return all cards belonging to any bank account of the contact.
        Useful for a flat listing, though the UI uses nested display.
        """
        if not contact_id:
            return []
        sql = """
            SELECT c.*
            FROM bank_card c
            JOIN bank_account a ON a.bank_account_id = c.bank_account_id
            WHERE a.contact_id = ?
        """
        return await self._conn().fetch_all(sql, (int(contact_id),))

    async def create(
        self,
        bank_account_id: int,
        card_number: str,
        card_holder_name: str,
        expiry_date: Optional[str] = None,
    ) -> Optional[int]:
        if not bank_account_id or not card_number or not card_holder_name:
            return None
        result = await db_insert(self._conn(), self.TABLE, {
            "bank_account_id":  int(bank_account_id),
            "card_number":      card_number,
            "card_holder_name": card_holder_name,
            "expiry_date":      expiry_date,
            "enabled":          1,
        })
        return result_last_id(result)

    async def update(self, card_id: int, **fields) -> bool:
        if not card_id:
            return False
        allowed = {
            "card_number", "card_holder_name", "expiry_date",
        }
        values = {k: v for k, v in fields.items() if k in allowed}
        if not values:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"bank_card_id": int(card_id)},
            values=values,
        )
        return result_ok(result)

    async def delete(self, card_id: int) -> bool:
        if not card_id:
            return False
        result = await db_delete(
            self._conn(),
            self.TABLE,
            where={"bank_card_id": int(card_id)},
        )
        return result_ok(result)

    async def set_enabled(self, card_id: int, enabled: bool) -> bool:
        """Set the enabled flag on a single card."""
        if not card_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"bank_card_id": int(card_id)},
            values={"enabled": 1 if enabled else 0},
        )
        return result_ok(result)

    async def set_enabled_by_account(self, account_id: int, enabled: bool) -> bool:
        if not account_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"bank_account_id": int(account_id)},
            values={"enabled": 1 if enabled else 0},
        )
        return result_ok(result)
