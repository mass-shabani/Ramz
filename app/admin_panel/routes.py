"""
Admin Panel Routes

GET  /settings/admin                     — renders the admin shell
POST /settings/admin/partials/{section}  — returns an HTML fragment

Extensions are resolved via component_service.prepare_context() and
injected into the template context under "ui_extensions".
"""
from typing import Any


def register_routes(
    http_api: Any,
    template_service: Any,
    db_service: Any,
    logger: Any,
    message_service: Any = None,
    component_service: Any = None,
    app: Any = None,
    admin_service: Any = None,
):
    """
    Register the /settings/admin routes.
    """

    # ------------------------------------------------------------
    # Helper: session + enabled + revoked
    # ------------------------------------------------------------
    async def _ensure_authenticated(request):
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
    # Helper: render error page
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

        context = {
            "profile":      profile,
            "current_user": current_user,
            "permissions":  permissions,
            "section":      section,
            "module_name":  "admin_panel",
        }

        if component_service:
            try:
                await component_service.prepare_context(
                    template_context=context,
                    points=["ui.user_menu.items", "ui.topbar.actions"],
                    user_id=user_id,
                    db_service=db_service,
                    app=app,
                )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"prepare_context failed: {exc}",
                        level="WARNING", tag="admin",
                    )

        try:
            html = await template_service.render(
                "admin_layout.html",
                context=context,
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
        "users":    "partials/users.html",
        "forms":    "partials/forms.html",
        "access":   "partials/access.html",
        "roles":    "partials/roles.html",
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

        context = {
            "profile":     profile,
            "permissions": permissions,
            "section":     section,
            "module_name": "admin_panel",
        }

        if component_service:
            try:
                await component_service.prepare_context(
                    template_context=context,
                    points=["ui.user_menu.items"],
                    user_id=user_id,
                    db_service=db_service,
                    app=app,
                )
            except Exception:
                pass

        try:
            html = await template_service.render(
                template_name,
                context=context,
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

    # ------------------------------------------------------------
    # POST /settings/admin/users/list — JSON endpoint for the users table
    # ------------------------------------------------------------
    def _build_form_actions(row):
        """Build the actions column for one form row."""
        form_id = row.get("form_id") or ""
        grants = int(row.get("grants_count") or 0)

        actions = [
            {
                "action": "edit-form",
                "icon": (
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M12 20h9"/>'
                    '<path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4z"/>'
                    '</svg>'
                ),
                "title": "Edit",
                "data": {"form-id": form_id},
            },
        ]

        if grants > 0:
            actions.append({
                "action": "delete-form",
                "icon": (
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M3 6h18"/>'
                    '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
                    '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
                    '</svg>'
                ),
                "title": "Cannot delete (has grants)",
                "variant": "danger",
                "data": {"form-id": form_id},
            })
        else:
            actions.append({
                "action": "delete-form",
                "icon": (
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M3 6h18"/>'
                    '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
                    '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
                    '</svg>'
                ),
                "title": "Delete",
                "variant": "danger",
                "data": {"form-id": form_id},
            })

        return actions

    # ------------------------------------------------------------
    # POST /settings/admin/users/list — JSON endpoint for the users table
    # ------------------------------------------------------------
    def _build_user_actions(u, current_rank):
        """Build the actions column for one user row."""
        if int(current_rank) <= int(u.role_rank or 0):
            return []

        return [
            {
                "action": "change-role",
                "icon": (
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M12 2 4 6v6c0 5 3.4 9.4 8 10 4.6-.6 8-5 8-10V6z"/>'
                    '</svg>'
                ),
                "title": "Change role",
                "variant": "",
                "data": {"user-id": str(u.user_id)},
            },
            {
                "action": "toggle-user",
                "icon": (
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M18.36 6.64a9 9 0 1 1-12.73 0"/>'
                    '<line x1="12" y1="2" x2="12" y2="12"/>'
                    '</svg>'
                ),
                "title": "Disable" if u.enabled else "Enable",
                "variant": "danger" if u.enabled else "",
                "data": {
                    "user-id": str(u.user_id),
                    "enabled": "1" if u.enabled else "0",
                },
            },
            {
                "action": "reset-password",
                "icon": (
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4"/>'
                    '</svg>'
                ),
                "title": "Reset password",
                "variant": "",
                "data": {"user-id": str(u.user_id)},
            },
        ]

    @http_api.post("/settings/admin/users/list",
                   response_class=http_api.JSONResponse)
    async def admin_users_list(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.users.manage"
            )
        except Exception:
            can_manage = False

        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            current_rank = await db_service.get_user_rank(user_id)
        except Exception:
            current_rank = 0

        try:
            body = await request.json()
        except Exception:
            body = {}

        query  = str(body.get("query") or "").strip()
        try:
            offset = max(0, int(body.get("offset") or 0))
        except (TypeError, ValueError):
            offset = 0
        try:
            limit = int(body.get("limit") or 20)
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(200, limit))

        try:
            rows  = await db_service.admin_list_users(
                query=query, offset=offset, limit=limit
            )
            total = await db_service.admin_count_users(query=query)
        except Exception as exc:
            if logger:
                logger.log(
                    f"admin_users_list failed: {exc}",
                    level="ERROR", tag="admin",
                )
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error"},
                status_code=500,
            )

        columns = [
            {"key": "_user",    "label": "User",     "type": "avatar"},
            {"key": "username", "label": "Username"},
            {"key": "_role",    "label": "Role",     "type": "badge"},
            {"key": "_status",  "label": "Status",   "type": "badge"},
            {"key": "_joined",  "label": "Joined",   "type": "date"},
            {"key": "_actions", "label": "Actions",  "type": "actions"},
        ]

        row_data = []
        for u in rows:
            role_variant  = "active" if u.role_id in ("admin", "manager") else "idle"
            status_variant = "active" if u.enabled else "pending"

            row_data.append({
                "_user": {
                    "initials":    u.initials,
                    "name":        u.full_name,
                    "email":       u.email or "",
                    "avatarClass": "avatar--indigo",
                },
                "username": u.username or "",
                "_role": {
                    "text":    u.role_name or "—",
                    "variant": role_variant,
                },
                "_status": {
                    "text":    "Active" if u.enabled else "Disabled",
                    "variant": status_variant,
                },
                "_joined": u.created_at.isoformat() if u.created_at else "",
                "_actions": _build_user_actions(u, current_rank),
            })

        return http_api.JSONResponse(
            content={
                "columns": columns,
                "rows":    row_data,
                "total":   total,
                "offset":  offset,
                "limit":   limit,
            },
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/users/set-role
    # ------------------------------------------------------------
    async def _verify_admin_password(user_id, password):
        if not password:
            return False
        try:
            return await db_service.verify_current_user_password(
                user_id, password
            )
        except Exception:
            return False

    @http_api.post("/settings/admin/users/set-role",
                   response_class=http_api.JSONResponse)
    async def admin_users_set_role(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.users.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        try:
            target_user_id = int(body.get("user_id") or 0)
        except (TypeError, ValueError):
            target_user_id = 0
        new_role_id = str(body.get("new_role_id") or "").strip()
        password = str(body.get("password") or "")

        if not target_user_id or not new_role_id:
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_data",
                         "message": "Missing user_id or new_role_id."},
                status_code=200,
            )

        if not await _verify_admin_password(user_id, password):
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_password",
                         "message": "The password you entered is incorrect."},
                status_code=200,
            )

        if not admin_service:
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error",
                         "message": "Admin service not available."},
                status_code=500,
            )

        try:
            ok, code = await admin_service.set_user_role(
                target_user_id, new_role_id, user_id
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"set_user_role failed: {exc}",
                    level="ERROR", tag="admin",
                )
            ok, code = False, "internal_error"

        if not ok:
            messages = {
                "insufficient_rank": "You do not have sufficient rank to modify this user.",
                "user_not_found": "User not found.",
                "role_not_found": "Role not found.",
                "internal_error": "Something went wrong. Please try again.",
            }
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": code or "internal_error",
                    "message": messages.get(code or "internal_error",
                                            "Something went wrong."),
                },
                status_code=200,
            )

        return http_api.JSONResponse(
            content={
                "status": "success",
                "message": f"Role changed to '{new_role_id}'.",
                "user_id": target_user_id,
            },
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/users/toggle
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/users/toggle",
                   response_class=http_api.JSONResponse)
    async def admin_users_toggle(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.users.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        try:
            target_user_id = int(body.get("user_id") or 0)
        except (TypeError, ValueError):
            target_user_id = 0
        enabled = bool(body.get("enabled"))
        password = str(body.get("password") or "")

        if not target_user_id:
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_data",
                         "message": "Missing user_id."},
                status_code=200,
            )

        if not await _verify_admin_password(user_id, password):
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_password",
                         "message": "The password you entered is incorrect."},
                status_code=200,
            )

        if not admin_service:
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error",
                         "message": "Admin service not available."},
                status_code=500,
            )

        try:
            ok, code = await admin_service.toggle_user(
                target_user_id, enabled, user_id
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"toggle_user failed: {exc}",
                    level="ERROR", tag="admin",
                )
            ok, code = False, "internal_error"

        if not ok:
            messages = {
                "insufficient_rank": "You do not have sufficient rank to modify this user.",
                "user_not_found": "User not found.",
                "internal_error": "Something went wrong. Please try again.",
            }
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": code or "internal_error",
                    "message": messages.get(code or "internal_error",
                                            "Something went wrong."),
                },
                status_code=200,
            )

        state = "enabled" if enabled else "disabled"
        return http_api.JSONResponse(
            content={
                "status": "success",
                "message": f"User {state}.",
                "user_id": target_user_id,
            },
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/users/reset-password
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/users/reset-password",
                   response_class=http_api.JSONResponse)
    async def admin_users_reset_password(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.users.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        try:
            target_user_id = int(body.get("user_id") or 0)
        except (TypeError, ValueError):
            target_user_id = 0
        password = str(body.get("password") or "")

        if not target_user_id:
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_data",
                         "message": "Missing user_id."},
                status_code=200,
            )

        if not await _verify_admin_password(user_id, password):
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_password",
                         "message": "The password you entered is incorrect."},
                status_code=200,
            )

        if not admin_service:
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error",
                         "message": "Admin service not available."},
                status_code=500,
            )

        try:
            ok, temp_password, code = await admin_service.reset_password(
                target_user_id, user_id
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"reset_password failed: {exc}",
                    level="ERROR", tag="admin",
                )
            ok, temp_password, code = False, None, "internal_error"

        if not ok:
            messages = {
                "insufficient_rank": "You do not have sufficient rank to modify this user.",
                "user_not_found": "User not found.",
                "internal_error": "Something went wrong. Please try again.",
            }
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": code or "internal_error",
                    "message": messages.get(code or "internal_error",
                                            "Something went wrong."),
                },
                status_code=200,
            )

        return http_api.JSONResponse(
            content={
                "status": "success",
                "message": "Password reset.",
                "user_id": target_user_id,
                "temp_password": temp_password,
            },
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/forms/list
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/forms/list",
                   response_class=http_api.JSONResponse)
    async def admin_forms_list(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.forms.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            rows = await db_service.admin_list_forms()
        except Exception as exc:
            if logger:
                logger.log(
                    f"admin_forms_list failed: {exc}",
                    level="ERROR", tag="admin",
                )
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error"},
                status_code=500,
            )

        columns = [
            {"key": "form_id",     "label": "Form ID",     "className": "mono"},
            {"key": "form_name",   "label": "Name"},
            {"key": "description", "label": "Description"},
            {"key": "_grants",     "label": "Grants",      "type": "badge"},
            {"key": "_status",     "label": "Status",      "type": "badge"},
            {"key": "_actions",    "label": "Actions",     "type": "actions"},
        ]

        row_data = []
        for row in rows:
            grants = int(row.get("grants_count") or 0)
            enabled = bool(row.get("enabled"))
            row_data.append({
                "form_id":     row.get("form_id") or "",
                "form_name":   row.get("form_name") or "",
                "description": row.get("description") or "",
                "_grants": {
                    "text": str(grants),
                    "variant": "active" if grants > 0 else "idle",
                },
                "_status": {
                    "text": "Enabled" if enabled else "Disabled",
                    "variant": "active" if enabled else "pending",
                },
                "_actions": _build_form_actions(row),
            })

        return http_api.JSONResponse(
            content={"columns": columns, "rows": row_data},
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/forms/create
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/forms/create",
                   response_class=http_api.JSONResponse)
    async def admin_forms_create(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.forms.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        form_id      = str(body.get("form_id") or "").strip()
        form_name    = str(body.get("form_name") or "").strip()
        description  = str(body.get("description") or "")
        enabled      = bool(body.get("enabled", True))
        password     = str(body.get("password") or "")

        if not form_name:
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_data",
                         "message": "Form name is required."},
                status_code=200,
            )

        if not await _verify_admin_password(user_id, password):
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_password",
                         "message": "The password you entered is incorrect."},
                status_code=200,
            )

        if not admin_service:
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error",
                         "message": "Admin service not available."},
                status_code=500,
            )

        try:
            ok, final_id, code = await admin_service.create_form(
                form_id=form_id,
                form_name=form_name,
                description=description,
                enabled=enabled,
                current_user_id=user_id,
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"create_form failed: {exc}",
                    level="ERROR", tag="admin",
                )
            ok, final_id, code = False, None, "internal_error"

        if not ok:
            messages = {
                "invalid_data":     "Form name is required.",
                "form_id_exists":   "A form with this ID already exists.",
                "form_name_exists": "A form with this name already exists.",
                "internal_error":   "Something went wrong. Please try again.",
            }
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": code or "internal_error",
                    "message": messages.get(code or "internal_error",
                                            "Something went wrong."),
                },
                status_code=200,
            )

        return http_api.JSONResponse(
            content={
                "status": "success",
                "message": f"Form '{final_id}' created.",
                "form_id": final_id,
            },
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/forms/update
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/forms/update",
                   response_class=http_api.JSONResponse)
    async def admin_forms_update(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.forms.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        form_id      = str(body.get("form_id") or "").strip()
        form_name    = str(body.get("form_name") or "").strip()
        description  = str(body.get("description") or "")
        enabled      = bool(body.get("enabled", True))
        password     = str(body.get("password") or "")

        if not form_id or not form_name:
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_data",
                         "message": "Form ID and name are required."},
                status_code=200,
            )

        if not await _verify_admin_password(user_id, password):
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_password",
                         "message": "The password you entered is incorrect."},
                status_code=200,
            )

        if not admin_service:
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error",
                         "message": "Admin service not available."},
                status_code=500,
            )

        try:
            ok, code = await admin_service.update_form(
                form_id=form_id,
                form_name=form_name,
                description=description,
                enabled=enabled,
                current_user_id=user_id,
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"update_form failed: {exc}",
                    level="ERROR", tag="admin",
                )
            ok, code = False, "internal_error"

        if not ok:
            messages = {
                "invalid_data":     "Form ID and name are required.",
                "form_not_found":   "Form not found.",
                "form_name_exists": "Another form already uses this name.",
                "internal_error":   "Something went wrong. Please try again.",
            }
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": code or "internal_error",
                    "message": messages.get(code or "internal_error",
                                            "Something went wrong."),
                },
                status_code=200,
            )

        return http_api.JSONResponse(
            content={
                "status": "success",
                "message": "Form updated.",
                "form_id": form_id,
            },
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/forms/delete
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/forms/delete",
                   response_class=http_api.JSONResponse)
    async def admin_forms_delete(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.forms.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        form_id  = str(body.get("form_id") or "").strip()
        password = str(body.get("password") or "")

        if not form_id:
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_data",
                         "message": "Form ID is required."},
                status_code=200,
            )

        if not await _verify_admin_password(user_id, password):
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_password",
                         "message": "The password you entered is incorrect."},
                status_code=200,
            )

        if not admin_service:
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error",
                         "message": "Admin service not available."},
                status_code=500,
            )

        try:
            ok, code, grants = await admin_service.delete_form(
                form_id=form_id,
                current_user_id=user_id,
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"delete_form failed: {exc}",
                    level="ERROR", tag="admin",
                )
            ok, code, grants = False, "internal_error", 0

        if not ok:
            messages = {
                "invalid_data":     "Form ID is required.",
                "form_not_found":   "Form not found.",
                "internal_error":   "Something went wrong. Please try again.",
            }
            if code == "form_has_grants":
                message = (
                    f"This form has {grants} active grant(s). "
                    "Remove all grants before deleting the form."
                )
            else:
                message = messages.get(code or "internal_error",
                                       "Something went wrong.")
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": code or "internal_error",
                    "message": message,
                    "grants": grants,
                },
                status_code=200,
            )

        return http_api.JSONResponse(
            content={
                "status": "success",
                "message": f"Form '{form_id}' deleted.",
            },
            status_code=200,
        )

    def _build_grant_actions(row):
        """Build the actions column for one grant row."""
        return [
            {
                "action": "edit-grant",
                "icon": (
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M12 20h9"/>'
                    '<path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4z"/>'
                    '</svg>'
                ),
                "title": "Change condition",
                "data": {
                    "role-id": row.get("role_id") or "",
                    "form-id": row.get("form_id") or "",
                },
            },
            {
                "action": "delete-grant",
                "icon": (
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M3 6h18"/>'
                    '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
                    '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
                    '</svg>'
                ),
                "title": "Delete grant",
                "variant": "danger",
                "data": {
                    "role-id": row.get("role_id") or "",
                    "form-id": row.get("form_id") or "",
                },
            },
        ]

    def _grant_row_payload(row):
        """Convert a repo row into the JSON shape used by the UI."""
        return {
            "role_id":   row.get("role_id") or "",
            "role_name": row.get("role_name") or row.get("role_id") or "",
            "form_id":   row.get("form_id") or "",
            "form_name": row.get("form_name") or row.get("form_id") or "",
            "level":     int(row.get("level") or 0),
        }

    # ------------------------------------------------------------
    # POST /settings/admin/access/list
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/access/list",
                   response_class=http_api.JSONResponse)
    async def admin_access_list(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.access.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        role_filter = str(body.get("role_filter") or "").strip()
        form_filter = str(body.get("form_filter") or "").strip()
        query       = str(body.get("query") or "").strip()

        try:
            current_rank = await db_service.get_user_rank(user_id)
        except Exception:
            current_rank = 0

        try:
            grants = await db_service.admin_list_grants(
                role_filter=role_filter,
                form_filter=form_filter,
                query=query,
            )
            roles        = await db_service.admin_list_roles()
            forms        = await db_service.admin_list_forms()
        except Exception as exc:
            if logger:
                logger.log(
                    f"admin_access_list failed: {exc}",
                    level="ERROR", tag="admin",
                )
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error"},
                status_code=500,
            )

        # Visible roles: only those with rank strictly lower than
        # current user's rank. This also excludes super-admin (max rank).
        visible_roles = [
            r for r in roles
            if int(r.get("rank") or 0) < int(current_rank)
        ]
        visible_role_ids = {r.get("role_id") for r in visible_roles}

        # If a specific role_filter was requested but that role is not
        # visible to the current user, return an empty result set.
        if role_filter and role_filter not in visible_role_ids:
            return http_api.JSONResponse(
                content={
                    "columns": [
                        {"key": "_role",  "label": "Role",    "type": "badge"},
                        {"key": "_form",  "label": "Form"},
                        {"key": "_level", "label": "Level",   "type": "badge"},
                        {"key": "_actions", "label": "Actions", "type": "actions"},
                    ],
                    "rows":  [],
                    "roles": [
                        {"role_id": r.get("role_id"),
                         "role_name": r.get("role_name")}
                        for r in visible_roles
                    ],
                    "forms": [
                        {"form_id": f.get("form_id"),
                         "form_name": f.get("form_name")}
                        for f in forms
                    ],
                },
                status_code=200,
            )

        # Filter grants to visible roles only.
        grants = [
            g for g in grants
            if (g.get("role_id") or "") in visible_role_ids
        ]

        role_options = [
            {"role_id": r.get("role_id"), "role_name": r.get("role_name")}
            for r in visible_roles
        ]
        form_options = [
            {"form_id": f.get("form_id"), "form_name": f.get("form_name")}
            for f in forms
        ]

        columns = [
            {"key": "_role",  "label": "Role",    "type": "badge"},
            {"key": "_form",  "label": "Form"},
            {"key": "_level", "label": "Level",   "type": "badge"},
            {"key": "_actions", "label": "Actions", "type": "actions"},
        ]

        row_data = []
        for row in grants:
            payload = _grant_row_payload(row)
            lvl = payload["level"]
            row_data.append({
                "_role": {
                    "text":    payload["role_name"],
                    "variant": "active" if payload["role_id"] in ("admin", "manager") else "idle",
                },
                "_form": f"{payload['form_name']}",
                "_level": {
                    "text":    "Closed" if lvl == 0 else f"Level {lvl}",
                    "variant": "idle" if lvl == 0 else
                               "active" if lvl <= 2 else
                               "pending",
                },
                "_actions": _build_grant_actions(payload),
                "_raw": payload,
            })

        response_payload = {
            "columns": columns,
            "rows":    row_data,
            "roles":   role_options,
            "forms":   form_options,
        }

        # Role summary (mini-matrix) — only for visible roles.
        if role_filter and role_filter in visible_role_ids:
            try:
                summary_rows = await db_service.admin_list_role_summary(role_filter)
            except Exception:
                summary_rows = []
            response_payload["role_summary"] = [
                {
                    "form_id":      (r.get("form_id") or ""),
                    "form_name":    (r.get("form_name") or ""),
                    "form_enabled": bool(r.get("form_enabled")),
                    "level":        (None if r.get("level") is None else int(r.get("level"))),
                }
                for r in summary_rows
            ]
            response_payload["role_summary_role_id"] = role_filter

        return http_api.JSONResponse(
            content=response_payload,
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/access/create
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/access/create",
                   response_class=http_api.JSONResponse)
    async def admin_access_create(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.access.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        role_id  = str(body.get("role_id") or "").strip()
        form_id  = str(body.get("form_id") or "").strip()
        password = str(body.get("password") or "")

        try:
            level = int(body.get("level", 1))
        except (TypeError, ValueError):
            level = 1
        if level < 0:
            level = 0

        if not role_id or not form_id:
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_data",
                         "message": "Role and form are required."},
                status_code=200,
            )

        if not await _verify_admin_password(user_id, password):
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_password",
                         "message": "The password you entered is incorrect."},
                status_code=200,
            )

        if not admin_service:
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error",
                         "message": "Admin service not available."},
                status_code=500,
            )

        try:
            ok, code = await admin_service.create_grant(
                role_id=role_id,
                form_id=form_id,
                level=level,
                current_user_id=user_id,
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"create_grant failed: {exc}",
                    level="ERROR", tag="admin",
                )
            ok, code = False, "internal_error"

        if not ok:
            messages = {
                "invalid_data":      "Role, form, and a valid level are required.",
                "exists":            "This grant already exists. Use 'Edit' to change its level.",
                "role_not_found":    "Role not found.",
                "form_not_found":    "Form not found.",
                "insufficient_rank": "You do not have sufficient rank to manage grants for this role.",
                "internal_error":    "Something went wrong. Please try again.",
            }
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": code or "internal_error",
                    "message": messages.get(code or "internal_error",
                                            "Something went wrong."),
                },
                status_code=200,
            )

        return http_api.JSONResponse(
            content={
                "status": "success",
                "message": f"Grant created for '{role_id}' on '{form_id}'.",
            },
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/access/update
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/access/update",
                   response_class=http_api.JSONResponse)
    async def admin_access_update(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.access.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        role_id  = str(body.get("role_id") or "").strip()
        form_id  = str(body.get("form_id") or "").strip()
        password = str(body.get("password") or "")

        try:
            level = int(body.get("level", 1))
        except (TypeError, ValueError):
            level = 1
        if level < 0:
            level = 0

        if not role_id or not form_id:
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_data",
                         "message": "Role, form, and condition are required."},
                status_code=200,
            )

        if not await _verify_admin_password(user_id, password):
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_password",
                         "message": "The password you entered is incorrect."},
                status_code=200,
            )

        if not admin_service:
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error",
                         "message": "Admin service not available."},
                status_code=500,
            )

        try:
            ok, code = await admin_service.update_grant_level(
                role_id=role_id,
                form_id=form_id,
                new_level=level,
                current_user_id=user_id,
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"update_grant_level failed: {exc}",
                    level="ERROR", tag="admin",
                )
            ok, code = False, "internal_error"

        if not ok:
            messages = {
                "invalid_data":      "Role, form, and a valid level are required.",
                "grant_not_found":   "Grant not found.",
                "role_not_found":    "Role not found.",
                "insufficient_rank": "You do not have sufficient rank to manage grants for this role.",
                "internal_error":    "Something went wrong. Please try again.",
            }
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": code or "internal_error",
                    "message": messages.get(code or "internal_error",
                                            "Something went wrong."),
                },
                status_code=200,
            )

        return http_api.JSONResponse(
            content={
                "status": "success",
                "message": "Grant condition updated.",
            },
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/access/delete
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/access/delete",
                   response_class=http_api.JSONResponse)
    async def admin_access_delete(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_manage = await db_service.has_access(
                user_id, "admin_panel.access.manage"
            )
        except Exception:
            can_manage = False
        if not can_manage:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        role_id  = str(body.get("role_id") or "").strip()
        form_id  = str(body.get("form_id") or "").strip()
        password = str(body.get("password") or "")

        if not role_id or not form_id:
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_data",
                         "message": "Role and form are required."},
                status_code=200,
            )

        if not await _verify_admin_password(user_id, password):
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_password",
                         "message": "The password you entered is incorrect."},
                status_code=200,
            )

        if not admin_service:
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error",
                         "message": "Admin service not available."},
                status_code=500,
            )

        try:
            ok, code = await admin_service.delete_grant(
                role_id=role_id,
                form_id=form_id,
                current_user_id=user_id,
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"delete_grant failed: {exc}",
                    level="ERROR", tag="admin",
                )
            ok, code = False, "internal_error"

        if not ok:
            messages = {
                "invalid_data":      "Role and form are required.",
                "grant_not_found":   "Grant not found.",
                "role_not_found":    "Role not found.",
                "insufficient_rank": "You do not have sufficient rank to manage grants for this role.",
                "internal_error":    "Something went wrong. Please try again.",
            }
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": code or "internal_error",
                    "message": messages.get(code or "internal_error",
                                            "Something went wrong."),
                },
                status_code=200,
            )

        return http_api.JSONResponse(
            content={
                "status": "success",
                "message": "Grant deleted.",
            },
            status_code=200,
        )

    # ------------------------------------------------------------
    # POST /settings/admin/roles/list — read-only roles view
    # ------------------------------------------------------------
    @http_api.post("/settings/admin/roles/list",
                   response_class=http_api.JSONResponse)
    async def admin_roles_list(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.JSONResponse(
                content={"status": "error", "code": "session_expired"},
                status_code=401,
            )

        if not await _has_admin_access(user_id):
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            can_view = await db_service.has_access(
                user_id, "admin_panel.roles.view"
            )
        except Exception:
            can_view = False
        if not can_view:
            return http_api.JSONResponse(
                content={"status": "error", "code": "no_permission"},
                status_code=403,
            )

        try:
            rows = await db_service.admin_list_roles_with_counts()
        except Exception as exc:
            if logger:
                logger.log(
                    f"admin_roles_list failed: {exc}",
                    level="ERROR", tag="admin",
                )
            return http_api.JSONResponse(
                content={"status": "error", "code": "internal_error"},
                status_code=500,
            )

        columns = [
            {"key": "role_id",   "label": "Role ID",     "className": "mono"},
            {"key": "role_name", "label": "Name"},
            {"key": "description", "label": "Description"},
            {"key": "_grants",   "label": "Grants",      "type": "badge"},
            {"key": "_status",   "label": "Status",      "type": "badge"},
            {"key": "_actions",  "label": "Actions",     "type": "actions"},
        ]

        row_data = []
        for row in rows:
            role_id = row.get("role_id") or ""
            grants  = int(row.get("grants_count") or 0)
            enabled = bool(row.get("enabled"))

            if role_id == "super-admin":
                actions = [{
                    "action": "view-grants",
                    "icon": (
                        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/>'
                        '<circle cx="12" cy="12" r="3"/>'
                        '</svg>'
                    ),
                    "title": "Super-admin grants are managed in system settings",
                    "data": {"role-id": role_id, "disabled": "1"},
                }]
            else:
                actions = [{
                    "action": "view-grants",
                    "icon": (
                        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/>'
                        '<circle cx="12" cy="12" r="3"/>'
                        '</svg>'
                    ),
                    "title": "View grants",
                    "data": {"role-id": role_id},
                }]

            row_data.append({
                "role_id":     role_id,
                "role_name":   row.get("role_name") or "",
                "description": row.get("description") or "",
                "_grants": {
                    "text":    str(grants),
                    "variant": "active" if grants > 0 else "idle",
                },
                "_status": {
                    "text":    "Enabled" if enabled else "Disabled",
                    "variant": "active" if enabled else "pending",
                },
                "_actions": actions,
            })

        return http_api.JSONResponse(
            content={"columns": columns, "rows": row_data},
            status_code=200,
        )


