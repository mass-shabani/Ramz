"""
Subscription repository.

Handles the `subscription` table (available plans: free, basic,
premium, enterprise).
"""
from typing import Optional


class SubscriptionRepository:

    TABLE = "subscription"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_id(self, subscription_id: int) -> Optional[dict]:
        """Return the subscription row for the given id, or None."""
        if not subscription_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"subscription_id": int(subscription_id)},
        )

    async def get_by_name(self, name: str) -> Optional[dict]:
        """Return the subscription row matching the given name, or None."""
        if not name:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"subscription_name": name},
        )

    async def list_enabled(self) -> list[dict]:
        """Return all enabled subscription plans."""
        return await self._conn().find_many(
            self.TABLE,
            where={"enabled": 1},
        )
