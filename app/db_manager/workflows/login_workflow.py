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


class LoginError(Exception):
    """
    Raised by `authenticate_strict` when authentication fails.

    Codes
    -----
    • "invalid_credentials" — username not found OR password wrong
                              (deliberately combined to prevent
                              username enumeration)
    • "account_disabled"    — user exists but is disabled
    • "invalid_data"        — username or password was empty
    """
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


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
    async def login_strict(
        self,
        username: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        """
        Same as login() but raises LoginError on failure with a code
        that describes the reason.

        Returns a User (without password_hash) on success.

        Raises
        ------
        LoginError
            with codes: invalid_credentials | account_disabled |
            invalid_data
        """
        if not username or not password:
            raise LoginError("invalid_data")

        user = await self._db._user_repo.get_by_username(
            username, include_password=True
        )

        # Unknown user → generic error (do NOT reveal that user doesn't exist)
        if user is None:
            self._log(
                f"Login failed: unknown user '{username}'",
                level="WARNING",
            )
            raise LoginError("invalid_credentials")

        # User found but disabled → specific error
        if not user.enabled:
            self._log(
                f"Login failed: user '{username}' is disabled",
                level="WARNING",
            )
            raise LoginError("account_disabled")

        # Wrong password → generic error (same as unknown user)
        if not user.password_hash or not verify_password(
            password, user.password_hash
        ):
            self._log(
                f"Login failed: bad password for '{username}'",
                level="WARNING",
            )
            raise LoginError("invalid_credentials")

        # Optional re-hash — same as login()
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
                self._log(
                    f"Password re-hash failed for user_id={user.user_id}: {exc}",
                    level="WARNING",
                )

        # Log successful login
        try:
            await self._db._activity_repo.log(
                user_id=user.user_id,
                type_name="login",
                ip_address=ip,
                user_agent=user_agent,
            )
        except Exception as exc:
            self._log(
                f"Failed to log login activity: {exc}",
                level="WARNING",
            )

        # 5.5 — Create a session record for this login
        session_id = self._generate_session_id()
        if session_id:
            try:
                from ..security.session_utils import describe_device
                await self._db._session_repo.create(
                    session_id=session_id,
                    user_id=user.user_id,
                    ip_address=ip,
                    user_agent=user_agent,
                    device_label=describe_device(user_agent),
                )
                user.session_id = session_id
            except Exception as exc:
                self._log(
                    f"Failed to create session record: {exc}",
                    level="WARNING",
                )

        user.password_hash = None
        return user

    async def login(
        self,
        username: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[User]:
        """
        Same as login_strict() but returns None on any failure.
        Provided for backward compatibility with existing callers.
        """
        try:
            return await self.login_strict(
                username, password, ip, user_agent
            )
        except LoginError:
            return None

    def _generate_session_id(self) -> Optional[str]:
        try:
            from ..security.session_utils import generate_session_id
            return generate_session_id()
        except Exception:
            return None

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
