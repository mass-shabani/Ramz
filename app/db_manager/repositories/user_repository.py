"""
User repository.

Handles reads for the `user` table. Because almost every caller needs
user data joined with `people`, `role`, `subscription`, `email` and
`phone`, the main read methods use a single JOIN query and return a
fully populated `User` object.

Writes (create / update / password change) will be added in later phases.
"""
from typing import Optional

from ..models.user import User


class UserRepository:

    TABLE = "user"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    # ----------------------------------------------------------
    # Internal SQL builder
    # ----------------------------------------------------------
    def _select_user_sql(self, include_password: bool = False) -> str:
        """
        Build the SELECT statement used by both read methods.

        The joins are LEFT JOIN so a user without an email, phone or
        subscription still appears in the result.
        """
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

    async def _find_one_user(self, where_clause: str, params: tuple,
                             include_password: bool = False) -> Optional[User]:
        """
        Run the JOIN query with the given WHERE clause and return a User.
        """
        sql = self._select_user_sql(include_password=include_password) \
            .replace("{{ where_clause }}", where_clause)

        row = await self._conn().fetch_one(sql, params)
        if not row:
            return None
        return User.from_row(row)

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get_by_username(self, username: str,
                              include_password: bool = False) -> Optional[User]:
        """
        Return a fully populated User by username, or None.

        Parameters
        ----------
        username : str
            The exact username to look up. Case sensitivity depends on
            the database collation (SQLite is case-sensitive by default).
        include_password : bool
            If True, the returned User will contain `password_hash`.
            Only login should pass True.
        """
        if not username:
            return None
        return await self._find_one_user(
            where_clause="u.username = ?",
            params=(username,),
            include_password=include_password,
        )

    async def get_by_id(self, user_id: int,
                        include_password: bool = False) -> Optional[User]:
        """
        Return a fully populated User by user_id, or None.
        """
        if not user_id:
            return None
        return await self._find_one_user(
            where_clause="u.user_id = ?",
            params=(int(user_id),),
            include_password=include_password,
        )

    async def is_enabled(self, user_id: int) -> bool:
        """
        Return True if the given user is enabled. False otherwise.
        Used by access control to check the current state of a user
        without loading the full row.
        """
        if not user_id:
            return False
        row = await self._conn().fetch_one(
            "SELECT enabled FROM user WHERE user_id = ? LIMIT 1",
            (int(user_id),),
        )
        if not row:
            return False
        # SQLite stores booleans as 0/1.
        return bool(row.get("enabled", 0))

    # ----------------------------------------------------------
    # Password updates (internal — used by login and settings)
    # ----------------------------------------------------------
    async def update_password_hash(
        self, user_id: int, password_hash: str
    ) -> bool:
        """
        Update the stored password hash for a user.

        Returns True if a row was updated, False otherwise.
        The caller is responsible for hashing the plaintext password
        before calling this method.
        """
        if not user_id or not password_hash:
            return False

        result = await self._conn().update(
            self.TABLE,
            where={"user_id": int(user_id)},
            values={"password_hash": password_hash},
        )
        # The framework's update() returns the number of affected rows,
        # or a QueryResult. Handle both.
        return _update_ok(result)


# --------------------------------------------------------------
# Helper
# --------------------------------------------------------------
def _update_ok(result) -> bool:
    """
    Interpret the return value of framework's update().

    Some framework versions return an int (affected rows), others
    return a QueryResult object with an 'affected_rows' or 'rowcount'
    attribute. This helper accepts any of them.
    """
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
    # If we can't tell, assume success (safer than breaking the flow).
    return True

