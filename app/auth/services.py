"""
Auth Service — handles login, logout, and session management.
"""
from typing import Optional, Dict, Any

from app.db_manager.workflows import LoginError


class AuthService:

    def __init__(self, db_service, logger=None):
        self.db = db_service
        self.logger = logger

    def _log(self, message, level="INFO"):
        if self.logger:
            try:
                self.logger.log(message, level=level, tag="auth")
            except Exception:
                pass

    # ----------------------------------------------------------
    # Login
    # ----------------------------------------------------------
    async def login(
        self,
        username: str,
        password: str,
        request,
    ) -> Optional[str]:
        """
        Attempt to authenticate a user.

        Returns
        -------
        str or None
            On success: None and the session is populated.
            On failure: an error code string suitable for the template:
                • "invalid_credentials"
                • "account_disabled"
                • "invalid_data"
                • "internal_error"
        """
        if not username or not password:
            return "invalid_data"

        ip = _get_client_ip(request)
        user_agent = _get_user_agent(request)

        try:
            user = await self.db.authenticate_strict(
                username=username,
                password=password,
                ip=ip,
                user_agent=user_agent,
            )
        except LoginError as exc:
            return exc.code
        except Exception as exc:
            self._log(f"Login internal error: {exc}", level="ERROR")
            return "internal_error"

        # Populate session
        request.session["user"] = {
            "user_id":    user.user_id,
            "username":   user.username,
            "full_name":  user.full_name,
            "initials":   user.initials,
            "role_id":    user.role_id,
            "role_name":  user.role_name,
            "email":      user.email,
            "phone":      user.phone,
        }
        return None

    # ----------------------------------------------------------
    # Logout
    # ----------------------------------------------------------
    async def logout(self, request) -> bool:
        """
        Clear the session and record a logout activity.
        """
        user_data = request.session.get("user") or {}
        user_id = user_data.get("user_id")

        if user_id:
            try:
                await self.db.log_activity(
                    user_id=user_id,
                    activity_type="logout",
                    ip=_get_client_ip(request),
                    user_agent=_get_user_agent(request),
                )
            except Exception:
                pass

        request.session.clear()
        return True

    # ----------------------------------------------------------
    # Session validation
    # ----------------------------------------------------------
    async def validate_session(self, request) -> bool:
        """
        Check whether the current session is still valid.

        A session becomes invalid if:
            • No user is stored in the session
            • The stored user_id is missing or malformed
            • The user has been disabled since the session started

        When invalid, the session is cleared so the next request is
        treated as a fresh visitor.

        Returns True if the session is valid, False otherwise.
        """
        user_data = None
        try:
            user_data = request.session.get("user")
        except Exception:
            return False

        if not user_data:
            return False

        user_id = user_data.get("user_id") if isinstance(user_data, dict) else None
        if not user_id:
            request.session.clear()
            return False

        try:
            enabled = await self.db.is_user_enabled(user_id)
        except Exception:
            # If we can't check, keep the user logged in (fail open).
            return True

        if not enabled:
            self._log(
                f"Session invalidated for user_id={user_id} (disabled)",
                level="WARNING",
            )
            request.session.clear()
            return False

        return True


# --------------------------------------------------------------
# Helpers
# --------------------------------------------------------------
def _get_client_ip(request) -> Optional[str]:
    if request is None:
        return None
    headers = getattr(request, "headers", None)
    if headers and hasattr(headers, "get"):
        for name in ("x-forwarded-for", "x-real-ip"):
            value = headers.get(name)
            if value:
                return value.split(",")[0].strip()
    client = getattr(request, "client", None)
    if client and hasattr(client, "host"):
        return client.host
    return None


def _get_user_agent(request) -> Optional[str]:
    if request is None:
        return None
    headers = getattr(request, "headers", None)
    if headers and hasattr(headers, "get"):
        return headers.get("user-agent")
    return None
