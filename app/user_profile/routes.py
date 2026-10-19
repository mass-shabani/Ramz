"""
Profile Routes

GET /profile — renders the authenticated user's profile page.
"""
from typing import Any


def register_routes(
    http_api: Any,
    template_service: Any,
    db_service: Any,
    logger: Any,
    message_service: Any = None,
):
    """
    Register the /profile route.
    """

    async def _render_error_page(status_code, title, message):
        """
        Render a styled error page (uses message_service first, then
        template_service error.html, then plain HTML).
        """
        # 1. Prefer message_service
        if message_service:
            try:
                html = await message_service.render_message(
                    status_code=status_code,
                    title=title,
                    message=message,
                    message_type="error",
                )
                return http_api.HTMLResponse(
                    content=html, status_code=status_code
                )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"message_service.render_message failed: {exc}",
                        level="WARNING", tag="profile",
                    )

        # 2. Fallback to template_service error.html
        try:
            html = await template_service.render(
                "error.html",
                context={
                    "status_code": status_code,
                    "title":       title,
                    "message":     message,
                    "module_name": "template_service",
                },
            )
            return http_api.HTMLResponse(
                content=html, status_code=status_code
            )
        except Exception:
            pass

        # 3. Plain text last resort
        return http_api.HTMLResponse(
            content=f"<h1>{status_code}</h1><p>{title}</p><p>{message}</p>",
            status_code=status_code,
        )

    # ------------------------------------------------------------
    # GET /profile — full profile page
    # ------------------------------------------------------------
    @http_api.get("/profile", response_class=http_api.HTMLResponse)
    async def profile_view(request: http_api.Request):
        """
        Render the current user's profile.

        Guards applied in order:
            1. Session must contain a user.
            2. The user must still be enabled (session validation).
            3. If access control is set up, the user must have the
               'user_profile.view' permission.
        """
        # 1. Session must contain a user
        current_user = (
            request.session.get("user")
            if hasattr(request, "session")
            else None
        )
        if not current_user:
            return http_api.RedirectResponse(url="/login", status_code=302)

        user_id = (
            current_user.get("user_id")
            if isinstance(current_user, dict)
            else None
        )
        if not user_id:
            try:
                request.session.clear()
            except Exception:
                pass
            return http_api.RedirectResponse(url="/login", status_code=302)

        # 2. Session validation — user must still be enabled
        try:
            enabled = await db_service.is_user_enabled(user_id)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Session check failed for user_id={user_id}: {exc}",
                    level="ERROR",
                    tag="profile",
                )
            enabled = True   # fail open on transient errors

        if not enabled:
            if logger:
                logger.log(
                    f"Session invalidated for user_id={user_id} (disabled)",
                    level="WARNING",
                    tag="profile",
                )
            try:
                request.session.clear()
            except Exception:
                pass
            return http_api.RedirectResponse(url="/login", status_code=302)

        # 3. Access check (optional — if form is registered)
        try:
            allowed = await db_service.has_access(
                user_id, "user_profile.view"
            )
        except Exception:
            allowed = True   # fail open

        if not allowed:
            return await _render_error_page(
                status_code=403,
                title="Access denied",
                message=(
                    "You do not have permission to view this page. "
                    "If you believe this is a mistake, please contact "
                    "an administrator."
                ),
            )

        # ------------------------------------------------------------
        # Fetch profile data
        # ------------------------------------------------------------
        try:
            profile = await db_service.get_full_profile(user_id)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Failed to load profile for user_id={user_id}: {exc}",
                    level="ERROR",
                    tag="profile",
                )
            profile = None

        if profile is None:
            return await _render_error_page(
                status_code=404,
                title="Profile not found",
                message="The requested profile could not be found.",
            )

        # ------------------------------------------------------------
        # Fetch recent activities (best-effort)
        # ------------------------------------------------------------
        try:
            activities = await db_service.get_user_activities(
                user_id, limit=10, offset=0
            )
        except Exception:
            activities = []

        try:
            activity_count = await db_service.count_user_activities(user_id)
        except Exception:
            activity_count = 0

        # ------------------------------------------------------------
        # Render
        # ------------------------------------------------------------
        try:
            html = await template_service.render(
                "profile.html",
                context={
                    "profile":        profile,
                    "current_user":   current_user,
                    "activities":     activities,
                    "activity_count": activity_count,
                    "module_name":    "user_profile",
                },
            )
            return http_api.HTMLResponse(content=html)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Error rendering profile: {exc}",
                    level="ERROR",
                    tag="profile",
                )
            return await _render_error_page(
                status_code=500,
                title="Internal error",
                message="Failed to render the profile page. Please try again later.",
            )
