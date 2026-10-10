"""
Login workflow.

Combines user lookup, password verification, optional re-hash, and
activity logging into one operation.

The workflow never returns a User that contains `password_hash`. That
field is stripped before returning.

Design notes
------------
• Failures are silent from the caller's point of view — the method
  returns None for any failure (unknown user, disabled user, wrong
  password) so the application can respond with a generic "invalid
  credentials" message that does not leak account existence.

• Activity logging happens ONLY on successful login. Failed login
  attempts are not logged here; a separate workflow or the caller may
  decide to log them for security auditing.
"""
from typing import Optional

from ..models.user import User
from ..security.password import verify_password, needs_rehash, hash_password


class LoginWorkflow:

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _log(self, message, level="INFO"):
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="database")
            except Exception:
                pass

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------
    async def login(
        self,
        username: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[User]:
        """
        Attempt to authenticate a user.

        Parameters
        ----------
        username : str
        password : str
        ip : str, optional
        user_agent : str, optional

        Returns
        -------
        User or None
            The authenticated user (without password_hash) on success,
            None on any failure.
        """
        if not username or not password:
            return None

        # 1) Look up the user including the password hash
        user = await self._db._user_repo.get_by_username(
            username, include_password=True
        )
        if user is None:
            self._log(f"Login failed: unknown user '{username}'", level="WARNING")
            return None

        # 2) Account must be enabled
        if not user.enabled:
            self._log(f"Login failed: user '{username}' is disabled", level="WARNING")
            return None

        # 3) Verify password
        if not user.password_hash or not verify_password(password, user.password_hash):
            self._log(f"Login failed: bad password for '{username}'", level="WARNING")
            return None

        # 4) Optional: re-hash if the cost factor is outdated
        if needs_rehash(user.password_hash):
            try:
                new_hash = hash_password(password)
                await self._db._user_repo.update_password_hash(
                    user.user_id, new_hash
                )
                self._log(
                    f"Password hash upgraded for user_id={user.user_id}"
                )
            except Exception as exc:
                # Re-hash is an optimisation — failure must not block login
                self._log(
                    f"Password re-hash failed for user_id={user.user_id}: {exc}",
                    level="WARNING",
                )

        # 5) Log successful login
        try:
            await self._db._activity_repo.log(
                user_id=user.user_id,
                type_name="login",
                ip_address=ip,
                user_agent=user_agent,
            )
        except Exception as exc:
            # Activity logging is best-effort and never blocks login
            self._log(f"Failed to log login activity: {exc}", level="WARNING")

        # 6) Strip password hash before returning
        user.password_hash = None
        return user

    # ----------------------------------------------------------
    # Optional: record a failed login
    # ----------------------------------------------------------
    async def log_failed_login(
        self,
        username: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Record a failed login attempt.

        This is optional — the caller decides whether failed logins
        should be logged. Only call this if the username actually
        exists in the database (to avoid leaking account existence
        through timing or log volume).

        Returns True if the activity was recorded, False otherwise.
        """
        user = await self._db._user_repo.get_by_username(username)
        if user is None:
            return False

        try:
            return await self._db._activity_repo.log(
                user_id=user.user_id,
                type_name="login_failed",
                ip_address=ip,
                user_agent=user_agent,
            )
        except Exception:
            return False
