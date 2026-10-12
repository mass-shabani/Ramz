"""
Account Setting Routes

GET /account/settings — renders the authenticated user's settings page.
"""
from typing import Any


def register_routes(
    http_api: Any,
    template_service: Any,
    db_service: Any,
    logger: Any,
):
    """
    Register the /account/settings route.
    """

    # ------------------------------------------------------------
    # GET /account/settings — full settings page
    # ------------------------------------------------------------
    @http_api.get("/account/settings", response_class=http_api.HTMLResponse)
    async def settings_view(request: http_api.Request):
        """
        Render the current user's account settings.

        Guards applied in order:
            1. Session must contain a user.
            2. The user must still be enabled.
            3. If access control is set up, the user must have the
               'account.setting.view' permission.
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
                    tag="settings",
                )
            enabled = True

        if not enabled:
            if logger:
                logger.log(
                    f"Session invalidated for user_id={user_id} (disabled)",
                    level="WARNING",
                    tag="settings",
                )
            try:
                request.session.clear()
            except Exception:
                pass
            return http_api.RedirectResponse(url="/login", status_code=302)

        # 3. Access check (optional)
        try:
            allowed = await db_service.has_access(
                user_id, "account.setting.view"
            )
        except Exception:
            allowed = True

        if not allowed:
            return http_api.HTMLResponse(
                content="<h1>Access denied</h1>"
                        "<p>You do not have permission to view this page.</p>",
                status_code=403,
            )

        # ------------------------------------------------------------
        # Fetch profile data (used across all settings sections)
        # ------------------------------------------------------------
        try:
            profile = await db_service.get_full_profile(user_id)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Failed to load profile for user_id={user_id}: {exc}",
                    level="ERROR",
                    tag="settings",
                )
            profile = None

        if profile is None:
            return http_api.HTMLResponse(
                content="<h1>Profile not found</h1>",
                status_code=404,
            )

        # ------------------------------------------------------------
        # Fetch permissions for the current user (which sections they can edit)
        # ------------------------------------------------------------
        async def _has(form_id):
            try:
                return await db_service.has_access(user_id, form_id)
            except Exception:
                return False

        permissions = {
            "profile_edit":  await _has("account.profile.edit"),
            "password":      await _has("account.password.change"),
            "twofa":         await _has("account.2fa.manage"),
            "banking":       await _has("account.banking.manage"),
            "sessions":      await _has("account.sessions.manage"),
            "delete":        await _has("account.delete"),
        }

        # ------------------------------------------------------------
        # Render
        # ------------------------------------------------------------
        try:
            html = await template_service.render(
                "settings.html",
                context={
                    "profile":      profile,
                    "current_user": current_user,
                    "permissions":  permissions,
                    "module_name":  "account_setting",
                },
            )
            return http_api.HTMLResponse(content=html)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Error rendering settings: {exc}",
                    level="ERROR",
                    tag="settings",
                )
            return http_api.HTMLResponse(
                content="<h1>Error</h1><p>Failed to render settings page.</p>",
                status_code=500,
            )
