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
        # Phase 3+: forms, access, roles will be added here
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
    def _build_user_actions(u, current_user_id):
        """Build the actions column for one user row."""
        if int(u.user_id) == int(current_user_id):
            return []
        if (u.role_name or "").lower() == "super-admin":
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
            role_lower    = (u.role_name or "").lower()
            role_variant  = "active" if role_lower in ("admin", "manager") else "idle"
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
                "_actions": _build_user_actions(u, user_id),
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
        new_role = str(body.get("new_role") or "").strip()
        password = str(body.get("password") or "")

        if not target_user_id or not new_role:
            return http_api.JSONResponse(
                content={"status": "error", "code": "invalid_data",
                         "message": "Missing user_id or new_role."},
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
                target_user_id, new_role, user_id
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
                "cannot_modify_self": "You cannot change your own role from this page.",
                "cannot_modify_super_admin": "Super-admin accounts cannot be modified here.",
                "cannot_promote_to_super_admin": "You cannot promote a user to super-admin.",
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
                "message": f"Role changed to '{new_role}'.",
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
                "cannot_modify_self": "You cannot change your own status from this page.",
                "cannot_modify_super_admin": "Super-admin accounts cannot be modified here.",
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
                "cannot_modify_self": "You cannot reset your own password from this page.",
                "cannot_modify_super_admin": "Super-admin accounts cannot be modified here.",
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

