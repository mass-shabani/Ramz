"""
User repository.

Handles reads and writes for the `user` table.
"""
from typing import Optional

from ..models.user import User
from ._helpers import (
    db_insert,
    db_update,
    result_ok,
    result_last_id,
)


class UserRepository:

    TABLE = "user"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # SQL builder
    # ----------------------------------------------------------
    def _select_user_sql(self, include_password: bool = False) -> str:
        password_col = "u.password_hash," if include_password else ""

        return f"""
            SELECT
                u.user_id,
                u.username,
                u.enabled,
                u.role_id,
                u.people_id,
                u.email_id,
                u.phone_id,
                u.subscription_id,
                u.xp_points,
                u.two_factor_enabled,
                u.created_at,
                u.updated_at,
                {password_col}
                p.first_name,
                p.last_name,
                p.birth_date,
                p.gender,
                p.national_code,
                r.role_name,
                s.subscription_name,
                e.email_address,
                ph.phone_number
            FROM user u
            JOIN      people        p  ON p.people_id       = u.people_id
            LEFT JOIN role          r  ON r.role_id         = u.role_id
            LEFT JOIN subscription  s  ON s.subscription_id = u.subscription_id
            LEFT JOIN email         e  ON e.email_id        = u.email_id
            LEFT JOIN phone         ph ON ph.phone_id       = u.phone_id
            WHERE {{{{ where_clause }}}}
            LIMIT 1
        """

    async def _find_one_user(
        self,
        where_clause: str,
        params: tuple,
        include_password: bool = False,
    ) -> Optional[User]:
        sql = self._select_user_sql(include_password=include_password) \
            .replace("{{ where_clause }}", where_clause)

        row = await self._conn().fetch_one(sql, params)
        if not row:
            return None
        return User.from_row(row)

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_username(
        self, username: str, include_password: bool = False
    ) -> Optional[User]:
        if not username:
            return None
        return await self._find_one_user(
            where_clause="u.username = ?",
            params=(username,),
            include_password=include_password,
        )

    async def get_by_id(
        self, user_id: int, include_password: bool = False
    ) -> Optional[User]:
        if not user_id:
            return None
        return await self._find_one_user(
            where_clause="u.user_id = ?",
            params=(int(user_id),),
            include_password=include_password,
        )

    async def is_enabled(self, user_id: int) -> bool:
        if not user_id:
            return False
        row = await self._conn().fetch_one(
            "SELECT enabled FROM user WHERE user_id = ? LIMIT 1",
            (int(user_id),),
        )
        if not row:
            return False
        return bool(row.get("enabled", 0))

    # ----------------------------------------------------------
    # Admin: list/count users (search + pagination)
    # ----------------------------------------------------------
    async def admin_list_users(
        self,
        query: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """
        List users for the admin panel with optional text search.

        The search term matches (case-insensitive LIKE) against
        username, first_name, last_name, and email_address.

        Returns a list of User objects, newest registered first.
        """
        if limit < 1:
            limit = 20
        if limit > 200:
            limit = 200
        if offset < 0:
            offset = 0

        search = f"%{(query or '').strip()}%"

        sql = """
            SELECT
                u.user_id,
                u.username,
                u.enabled,
                u.role_id,
                u.people_id,
                u.email_id,
                u.phone_id,
                u.subscription_id,
                u.xp_points,
                u.two_factor_enabled,
                u.created_at,
                u.updated_at,
                p.first_name,
                p.last_name,
                r.role_name,
                s.subscription_name,
                e.email_address,
                ph.phone_number
            FROM user u
            JOIN      people        p  ON p.people_id       = u.people_id
            LEFT JOIN role          r  ON r.role_id         = u.role_id
            LEFT JOIN subscription  s  ON s.subscription_id = u.subscription_id
            LEFT JOIN email         e  ON e.email_id        = u.email_id
            LEFT JOIN phone         ph ON ph.phone_id       = u.phone_id
            WHERE (
                u.username   LIKE ? OR
                p.first_name LIKE ? OR
                p.last_name  LIKE ? OR
                e.email_address LIKE ?
            )
            ORDER BY u.user_id DESC
            LIMIT ? OFFSET ?
        """
        rows = await self._conn().fetch_all(
            sql, (search, search, search, search, limit, offset)
        )
        return [User.from_row(row) for row in rows or []]

    async def admin_count_users(self, query: str = "") -> int:
        """
        Count users matching the same search term as admin_list_users.
        """
        search = f"%{(query or '').strip()}%"

        sql = """
            SELECT COUNT(*) AS c
            FROM user u
            JOIN      people p ON p.people_id = u.people_id
            LEFT JOIN email  e ON e.email_id  = u.email_id
            WHERE (
                u.username   LIKE ? OR
                p.first_name LIKE ? OR
                p.last_name  LIKE ? OR
                e.email_address LIKE ?
            )
        """
        row = await self._conn().fetch_one(
            sql, (search, search, search, search)
        )
        return int(row["c"]) if row else 0

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def create(
        self,
        people_id: int,
        role_id: str,
        username: str,
        password_hash: str,
        email_id: Optional[int] = None,
        phone_id: Optional[int] = None,
        subscription_id: Optional[int] = None,
    ) -> Optional[int]:
        if not people_id or not role_id or not username or not password_hash:
            return None

        result = await db_insert(self._conn(), self.TABLE, {
            "people_id":          int(people_id),
            "role_id":            role_id,
            "username":           username,
            "password_hash":      password_hash,
            "email_id":           int(email_id) if email_id else None,
            "phone_id":           int(phone_id) if phone_id else None,
            "subscription_id":    int(subscription_id) if subscription_id else None,
            "enabled":            1,
            "xp_points":          0,
            "two_factor_enabled": 0,
        })
        return result_last_id(result)

    async def update_password_hash(
        self, user_id: int, password_hash: str
    ) -> bool:
        if not user_id or not password_hash:
            return False

        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"user_id": int(user_id)},
            values={"password_hash": password_hash},
        )
        return result_ok(result)

    async def update_role(
        self, user_id: int, role_id: str
    ) -> bool:
        """Change the user's role (by role_id TEXT)."""
        if not user_id or not role_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"user_id": int(user_id)},
            values={"role_id": role_id},
        )
        return result_ok(result)

    async def set_enabled(
        self, user_id: int, enabled: bool
    ) -> bool:
        """Enable or disable the user account."""
        if not user_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"user_id": int(user_id)},
            values={"enabled": 1 if enabled else 0},
        )
        return result_ok(result)

    async def update_email_id(
        self, user_id: int, email_id: Optional[int]
    ) -> bool:
        if not user_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"user_id": int(user_id)},
            values={"email_id": int(email_id) if email_id else None},
        )
        return result_ok(result)

    async def update_phone_id(
        self, user_id: int, phone_id: Optional[int]
    ) -> bool:
        if not user_id:
            return False
        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"user_id": int(user_id)},
            values={"phone_id": int(phone_id) if phone_id else None},
        )
        return result_ok(result)

    async def set_2fa(
        self,
        user_id: int,
        enabled: bool,
        secret: Optional[str] = None,
        backup_codes: Optional[str] = None,
    ) -> bool:
        if not user_id:
            return False

        values = {"two_factor_enabled": 1 if enabled else 0}
        if enabled:
            if not secret or not backup_codes:
                return False
            values["two_factor_secret"] = secret
            values["two_factor_backup_codes"] = backup_codes
        else:
            values["two_factor_secret"] = None
            values["two_factor_backup_codes"] = None

        result = await db_update(
            self._conn(),
            self.TABLE,
            where={"user_id": int(user_id)},
            values=values,
        )
        return result_ok(result)

    async def get_2fa_data(self, user_id: int) -> Optional[dict]:
        if not user_id:
            return None
        return await self._conn().fetch_one(
            "SELECT two_factor_enabled, two_factor_secret, "
            "two_factor_backup_codes "
            "FROM user WHERE user_id = ? LIMIT 1",
            (int(user_id),),
        )
