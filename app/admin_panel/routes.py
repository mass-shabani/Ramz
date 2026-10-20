"""
Admin Panel Routes

GET  /settings/admin                     — renders the admin shell
POST /settings/admin/partials/{section}  — returns an HTML fragment
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
    Register the /settings/admin routes.
    """

    # ------------------------------------------------------------
    # Helper: session + enabled + revoked
    # ------------------------------------------------------------
    async def _ensure_authenticated(request):
        """
        Return (user_id, None) on success, (None, response) on failure.
        """
        current_user = (
            request.session.get("user")
            if hasattr(request, "session")
            else None
        )
        if not current_user:
            return None, http_api.RedirectResponse(
                url="/login", status_code=302
            )

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
            return None, http_api.RedirectResponse(
                url="/login", status_code=302
            )

        try:
            enabled = await db_service.is_user_enabled(user_id)
        except Exception:
            enabled = True
        if not enabled:
            try:
                request.session.clear()
            except Exception:
                pass
            return None, http_api.RedirectResponse(
                url="/", status_code=302
            )

        try:
            session_id = request.session.get("session_id")
        except Exception:
            session_id = None

        if session_id:
            try:
                valid = await db_service.is_session_valid(session_id)
            except Exception:
                valid = True
            if not valid:
                try:
                    request.session.clear()
                except Exception:
                    pass
                return None, http_api.RedirectResponse(
                    url="/", status_code=302
                )

        return user_id, None

    # ------------------------------------------------------------
    # Helper: render error page (message_service → error.html → plain)
    # ------------------------------------------------------------
    async def _render_error_page(status_code, title, message):
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
                        level="WARNING", tag="admin",
                    )

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

        return http_api.HTMLResponse(
            content=f"<h1>{status_code}</h1><p>{title}</p><p>{message}</p>",
            status_code=status_code,
        )

    # ------------------------------------------------------------
    # Helper: check admin_panel.view
    # ------------------------------------------------------------
    async def _has_admin_access(user_id):
        try:
            return await db_service.has_access(user_id, "admin_panel.view")
        except Exception:
            return False

    # ------------------------------------------------------------
    # GET /settings/admin — shell
    # ------------------------------------------------------------
    @http_api.get("/settings/admin", response_class=http_api.HTMLResponse)
    async def admin_view(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return redirect

        if not await _has_admin_access(user_id):
            return await _render_error_page(
                status_code=403,
                title="Access denied",
                message=(
                    "You do not have permission to access the admin panel. "
                    "If you believe this is a mistake, please contact a "
                    "super-administrator."
                ),
            )

        current_user = request.session.get("user")

        try:
            profile = await db_service.get_full_profile(user_id)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Failed to load profile for user_id={user_id}: {exc}",
                    level="ERROR", tag="admin",
                )
            profile = None

        if profile is None:
            return await _render_error_page(
                status_code=404,
                title="Profile not found",
                message="The requested profile could not be found.",
            )

        qp = getattr(request, "query_params", {}) or {}
        section = qp.get("section") or "overview"
        valid_sections = {"overview", "users", "forms", "access", "roles"}
        if section not in valid_sections:
            section = "overview"

        async def _has(form_id):
            try:
                return await db_service.has_access(user_id, form_id)
            except Exception:
                return False

        permissions = {
            "users":  await _has("admin_panel.users.manage"),
            "forms":  await _has("admin_panel.forms.manage"),
            "access": await _has("admin_panel.access.manage"),
            "roles":  await _has("admin_panel.roles.view"),
        }

        try:
            html = await template_service.render(
                "admin_layout.html",
                context={
                    "profile":      profile,
                    "current_user": current_user,
                    "permissions":  permissions,
                    "section":      section,
                    "module_name":  "admin_panel",
                },
            )
            return http_api.HTMLResponse(content=html)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Error rendering admin shell: {exc}",
                    level="ERROR", tag="admin",
                )
            return await _render_error_page(
                status_code=500,
                title="Internal error",
                message="Failed to render the admin panel.",
            )

    # ------------------------------------------------------------
    # POST /settings/admin/partials/{section}
    # ------------------------------------------------------------
    PARTIAL_TEMPLATES = {
        "overview": "partials/overview.html",
        # Phase 3+: users, forms, access, roles will be added here
    }

    @http_api.post("/settings/admin/partials/{section}",
                   response_class=http_api.HTMLResponse)
    async def admin_partial(request: http_api.Request, section: str):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.HTMLResponse(
                content="<div class='card'><p>Session expired.</p></div>",
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.HTMLResponse(
                content="<div class='card'><p>Access denied.</p></div>",
                status_code=403,
            )

        template_name = PARTIAL_TEMPLATES.get(section)
        if not template_name:
            template_name = "partials/coming-soon.html"

        try:
            profile = await db_service.get_full_profile(user_id)
        except Exception:
            profile = None

        if profile is None:
            return http_api.HTMLResponse(
                content="<div class='card'><p>Profile not found.</p></div>",
                status_code=404,
            )

        try:
            html = await template_service.render(
                template_name,
                context={
                    "profile":     profile,
                    "section":     section,
                    "module_name": "admin_panel",
                },
            )
            return http_api.HTMLResponse(content=html)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Error rendering admin partial '{section}': {exc}",
                    level="ERROR", tag="admin",
                )
            return http_api.HTMLResponse(
                content="<div class='card'><p>Failed to load section.</p></div>",
                status_code=500,
            )
