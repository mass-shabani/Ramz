"""
User session repository.

Manages the `user_session` table.
"""
from datetime import datetime, timedelta
from typing import Optional

from ._helpers import db_insert, db_update, db_delete, result_ok


class SessionRepository:

    TABLE = "user_session"
    DEFAULT_LIFETIME_DAYS = 30

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    def _log(self, message, level="INFO"):
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="database")
            except Exception:
                pass

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def create(
        self,
        session_id: str,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_label: Optional[str] = None,
        lifetime_days: int = DEFAULT_LIFETIME_DAYS,
    ) -> bool:
        if not session_id or not user_id:
            return False
        try:
            expires = (
                datetime.utcnow() + timedelta(days=lifetime_days)
            ).strftime("%Y-%m-%d %H:%M:%S")

            result = await db_insert(self._conn(), self.TABLE, {
                "session_id":   session_id,
                "user_id":      int(user_id),
                "ip_address":   ip_address,
                "user_agent":   user_agent,
                "device_label": device_label,
                "expires_at":   expires,
                "revoked":      0,
            })
            return result_ok(result)
        except Exception as exc:
            self._log(f"session create failed: {exc}", level="ERROR")
            return False

    async def touch(self, session_id: str) -> bool:
        if not session_id:
            return False
        try:
            result = await db_update(
                self._conn(),
                self.TABLE,
                where={"session_id": session_id},
                values={"last_seen_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")},
            )
            return result_ok(result)
        except Exception:
            return False

    async def revoke(self, session_id: str) -> bool:
        if not session_id:
            return False
        try:
            result = await db_update(
                self._conn(),
                self.TABLE,
                where={"session_id": session_id},
                values={"revoked": 1},
            )
            return result_ok(result)
        except Exception as exc:
            self._log(f"session revoke failed: {exc}", level="ERROR")
            return False

    async def revoke_all_for_user(
        self, user_id: int, except_session_id: Optional[str] = None
    ) -> bool:
        if not user_id:
            return False
        try:
            if except_session_id:
                sql = (
                    "UPDATE user_session SET revoked = 1 "
                    "WHERE user_id = ? AND session_id != ? AND revoked = 0"
                )
                await self._conn().execute(sql, (int(user_id), except_session_id))
            else:
                sql = (
                    "UPDATE user_session SET revoked = 1 "
                    "WHERE user_id = ? AND revoked = 0"
                )
                await self._conn().execute(sql, (int(user_id),))
            return True
        except Exception as exc:
            self._log(f"revoke_all_for_user failed: {exc}", level="ERROR")
            return False

    async def delete(self, session_id: str) -> bool:
        if not session_id:
            return False
        try:
            result = await db_delete(
                self._conn(),
                self.TABLE,
                where={"session_id": session_id},
            )
            return result_ok(result)
        except Exception as exc:
            self._log(f"session delete failed: {exc}", level="ERROR")
            return False

    async def prune_expired(self, older_than_days: int = 90) -> bool:
        try:
            cutoff = (
                datetime.utcnow() - timedelta(days=older_than_days)
            ).strftime("%Y-%m-%d %H:%M:%S")
            await self._conn().execute(
                "DELETE FROM user_session WHERE expires_at < ?",
                (cutoff,),
            )
            return True
        except Exception:
            return False

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_id(self, session_id: str) -> Optional[dict]:
        if not session_id:
            return None
        return await self._conn().find_one(
            self.TABLE,
            where={"session_id": session_id},
        )

    async def list_active_for_user(self, user_id: int) -> list[dict]:
        if not user_id:
            return []
        try:
            rows = await self._conn().fetch_all(
                """
                SELECT session_id, user_id, ip_address, user_agent,
                       device_label, created_at, last_seen_at, expires_at
                FROM user_session
                WHERE user_id = ? AND revoked = 0
                ORDER BY last_seen_at DESC, created_at DESC
                """,
                (int(user_id),),
            )
            return rows or []
        except Exception as exc:
            self._log(f"list_active_for_user failed: {exc}", level="ERROR")
            return []

    async def count_active_for_user(self, user_id: int) -> int:
        if not user_id:
            return 0
        try:
            row = await self._conn().fetch_one(
                "SELECT COUNT(*) AS c FROM user_session "
                "WHERE user_id = ? AND revoked = 0",
                (int(user_id),),
            )
            return int(row["c"]) if row else 0
        except Exception:
            return 0
