"""
Panel Routes — HTTP endpoints for the user panel.

Endpoints:
    GET  /panel            → renders the full panel shell (sidebar + topbar + container)
    POST /panel/{view}     → returns an HTML fragment for the requested view
                             (used by the content-container component)

All framework access (Request, Response classes, etc.) is obtained from the
`http_api` argument supplied by the module, so no direct FastAPI imports are
needed.
"""
from typing import Any


# ============================================================
# View registry
# ------------------------------------------------------------
# Maps the path segment after "/panel/" to the partial template
# that should be rendered. Add new entries as pages are ported.
# ============================================================
VIEW_TEMPLATES = {
    "dashboard": "partials/dashboard-content.html",
    # "analytics":   "partials/analytics-content.html",
    # "predictions": "partials/predictions-content.html",
    # "markets":     "partials/markets-content.html",
    # "portfolio":   "partials/portfolio-content.html",
    # "alerts":      "partials/alerts-content.html",
    # "settings":    "partials/settings-content.html",
}


# ============================================================
# Helpers
# ============================================================
def _get_current_user(request):
    """Return the authenticated user object from the session, or None."""
    try:
        return request.session.get("user") if hasattr(request, "session") else None
    except Exception:
        return None


def _display_name(user) -> str:
    """Best-effort human-readable name for the user."""
    if user is None:
        return "User"
    if isinstance(user, dict):
        return user.get("full_name") or user.get("username") or "User"
    return (
        getattr(user, "full_name", None)
        or getattr(user, "username", None)
        or "User"
    )


def _initials(name: str) -> str:
    if not name:
        return "U"
    parts = [p for p in name.strip().split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper()


# ============================================================
# Session guard
# ============================================================
async def _check_session(request, db_service, auth_service, logger):
    """
    Return None if the session is valid.
    Return a response (RedirectResponse or JSON 401) if not.
    """
    user = _get_current_user(request)
    if not user:
        return None   # handled by caller-specific redirect

    user_id = user.get("user_id") if isinstance(user, dict) else None
    if not user_id:
        try:
            request.session.clear()
        except Exception:
            pass
        return None

    # 1. Enabled check
    try:
        enabled = db_service and await db_service.is_user_enabled(user_id)
    except Exception:
        enabled = True

    if not enabled:
        if logger:
            logger.log(
                f"Session invalidated for user_id={user_id} (disabled)",
                level="WARNING", tag="panel",
            )
        try:
            request.session.clear()
        except Exception:
            pass
        return "session_invalid"

    # 2. Revoked session check
    try:
        session_id = request.session.get("session_id")
    except Exception:
        session_id = None

    if session_id and db_service:
        try:
            valid = await db_service.is_session_valid(session_id)
        except Exception:
            valid = True

        if not valid:
            if logger:
                logger.log(
                    f"Session revoked for user_id={user_id}",
                    level="WARNING", tag="panel",
                )
            try:
                request.session.clear()
            except Exception:
                pass
            return "session_invalid"

    return None


# ============================================================
# Route registration
# ============================================================
def register_routes(
    http_api: Any,
    panel_service: Any,
    message_service: Any,
    logger: Any,
    db_service: Any = None,
):
    """
    Register user panel routes with the HTTP API.

    Parameters
    ----------
    http_api : the HTTP service exposed via the module context
    panel_service : the PanelService instance created by the module
    logger : shared logger from the module context
    """

    # ------------------------------------------------------------
    # GET /panel — full panel shell
    # ------------------------------------------------------------
    @http_api.get("/panel", response_class=http_api.HTMLResponse)
    async def panel_view(request: http_api.Request):
        """
        Render the panel shell (sidebar + topbar + empty container).
        The container will asynchronously request the initial view.
        """
        current_user = _get_current_user(request)
        if not current_user:
            return http_api.RedirectResponse(url="/login", status_code=302)

        # Full session validation (enabled + not revoked)
        check = await _check_session(request, db_service, None, logger)
        if check == "session_invalid":
            # Revoked or disabled → back to home
            return http_api.RedirectResponse(url="/", status_code=302)

        try:
            html_content = await panel_service.render_panel_view(
                "dashboard.html",
                {
                    "module_name":   "user_panel",
                    "current_user":  current_user,
                    "user_name":     _display_name(current_user),
                    "user_initials": _initials(_display_name(current_user)),
                },
                request,
            )
            return http_api.HTMLResponse(content=html_content)

        except Exception as e:
            if logger:
                logger.log(f"Error rendering panel shell: {e}", level="ERROR", tag="panel")
            if message_service:
                error_html = await message_service.render_message(
                    status_code=500,
                    title="Internal Server Error",
                    message="Failed to load panel. Please try again later.",
                    message_type="error"
                )
                return http_api.HTMLResponse(content=error_html, status_code=500)
            return http_api.HTMLResponse(
                content="<h1>500 — Internal Server Error</h1><p>Failed to load panel.</p>",
                status_code=500,
            )

    # ------------------------------------------------------------
    # POST /panel/{view} — content fragment loader
    # ------------------------------------------------------------
    @http_api.post("/panel/{view}", response_class=http_api.HTMLResponse)
    async def panel_partial(request: http_api.Request, view: str):
        """
        Return an HTML fragment for the requested view.

        Called by the <content-container> Lit component when a sidebar
        item is clicked. The returned HTML replaces the container's
        inner content without a full page reload.
        """
        current_user = _get_current_user(request)
        if not current_user:
            return http_api.JSONResponse(
                content={"status": "session_revoked", "message": "Session expired."},
                status_code=401,
            )

        # Full session validation
        check = await _check_session(request, db_service, None, logger)
        if check == "session_invalid":
            return http_api.JSONResponse(
                content={"status": "session_revoked", "message": "Session revoked."},
                status_code=401,
            )

        # --- Look up the partial template ---
        template_name = VIEW_TEMPLATES.get(view)
        if not template_name:
            if message_service:
                error_html = await message_service.render_message(
                    status_code=404,
                    title="Page Not Found",
                    message="The page you are looking for does not exist.",
                    message_type="error"
                )
                return http_api.HTMLResponse(content=error_html, status_code=404)
            return http_api.HTMLResponse(
                content="<div class='card'><p>Page not available yet.</p></div>",
                status_code=404,
            )

        # --- Render ---
        try:
            html_content = await panel_service.render_panel_view(
                template_name,
                {
                    "module_name": "user_panel",
                    "user_name":   _display_name(current_user),
                },
                request,
            )
            return http_api.HTMLResponse(content=html_content)

        except Exception as e:
            if logger:
                logger.log(
                    f"Error rendering partial '{view}': {e}",
                    level="ERROR",
                    tag="panel",
                )
            if message_service:
                error_html = await message_service.render_message(
                    status_code=500,
                    title="Internal Server Error",
                    message="Failed to load content. Please try again later.",
                    message_type="error"
                )
                return http_api.HTMLResponse(content=error_html, status_code=500)
            return http_api.HTMLResponse(
                content="<div class='card'><p>Failed to load content.</p></div>",
                status_code=500,
            )