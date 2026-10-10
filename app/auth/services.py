"""
Auth Service - Handles business logic for authentication.
"""
from typing import Optional

# --------------------------------------------------------------
# Helpers
# --------------------------------------------------------------
def _get_client_ip(request) -> str | None:
    """Best-effort extraction of the client IP from the request."""
    if request is None:
        return None
    headers = getattr(request, "headers", None)
    if headers:
        # Common proxy headers
        for name in ("x-forwarded-for", "x-real-ip"):
            value = headers.get(name) if hasattr(headers, "get") else None
            if value:
                return value.split(",")[0].strip()
    client = getattr(request, "client", None)
    if client and hasattr(client, "host"):
        return client.host
    return None


def _get_user_agent(request) -> str | None:
    """Best-effort extraction of the user-agent header."""
    if request is None:
        return None
    headers = getattr(request, "headers", None)
    if headers and hasattr(headers, "get"):
        return headers.get("user-agent")
    return None


class AuthService:
    """
    Provides authentication methods using the app_db_service.
    """

    def __init__(self, db_service, logger, legacy_db=None):
        self.db = db_service
        self.legacy_db = legacy_db
        self.logger = logger

    async def login(self, username: str, password: str, request) -> bool:
        """
        Authenticate a user via the new db_manager service.

        Extracts IP and user-agent from the request for activity logging.
        On success, stores the user dict in the session.
        """
        # Extract client info for activity logging
        ip = _get_client_ip(request)
        user_agent = _get_user_agent(request)

        user = await self.db.authenticate(
            username=username,
            password=password,
            ip=ip,
            user_agent=user_agent,
        )

        if not user:
            return False

        # Store session data (adjust the shape if the old code used something else)
        request.session["user"] = {
            "user_id": user.user_id,
            "username": user.username,
            "full_name": user.full_name,
            "initials": user.initials,
            "role_id": user.role_id,
            "role_name": user.role_name,
            "email": user.email,
            "phone": user.phone,
        }
        return True

    async def logout(self, request) -> bool:
        """
        Clear the session and record the logout activity.
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
                # Never block logout on activity logging failure
                pass

        request.session.clear()
        return True
