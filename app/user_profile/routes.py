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
):
    """
    Register the /profile route.
    """

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
            return http_api.HTMLResponse(
                content="<h1>Access denied</h1>"
                        "<p>You do not have permission to view this page.</p>",
                status_code=403,
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
            return http_api.HTMLResponse(
                content="<h1>Profile not found</h1>",
                status_code=404,
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
            return http_api.HTMLResponse(
                content="<h1>Error</h1><p>Failed to render profile page.</p>",
                status_code=500,
            )
