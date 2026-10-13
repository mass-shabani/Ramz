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
        # Extract flash message from query params
        qp = getattr(request, "query_params", {}) or {}
        flash_status = qp.get("status")
        flash_section = qp.get("section")
        flash_code = qp.get("code")

        try:
            html = await template_service.render(
                "settings.html",
                context={
                    "profile":       profile,
                    "current_user":  current_user,
                    "permissions":   permissions,
                    "flash_status":  flash_status,
                    "flash_section": flash_section,
                    "flash_code":    flash_code,
                    "module_name":   "account_setting",
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

    # ------------------------------------------------------------
    # Helper: apply the same guards as settings_view
    # ------------------------------------------------------------
    async def _ensure_authenticated(request):
        """
        Return (user_id, None) on success, or (None, response) if the
        request should be redirected.
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
                url="/login", status_code=302
            )

        return user_id, None

    async def _refresh_session(request, user_id):
        """
        Re-read the profile and update the session user dict so that
        subsequent page loads show fresh data.
        """
        try:
            fresh = await db_service.get_full_profile(user_id)
            if not fresh:
                return
            from app.db_manager.models import build_session_user
            request.session["user"] = build_session_user(fresh)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Session refresh failed for user_id={user_id}: {exc}",
                    level="WARNING",
                    tag="settings",
                )

    def _redirect(request, status, section, code=None):
        """Build a redirect back to /account/settings with query params."""
        from urllib.parse import urlencode
        params = {"status": status, "section": section}
        if code:
            params["code"] = code
        query = urlencode(params)
        return http_api.RedirectResponse(
            url=f"/account/settings?{query}", status_code=302
        )

    def _client_info(request):
        """Best-effort extraction of IP and user-agent."""
        ip = None
        ua = None
        headers = getattr(request, "headers", None)
        if headers and hasattr(headers, "get"):
            xff = headers.get("x-forwarded-for")
            if xff:
                ip = xff.split(",")[0].strip()
            else:
                ip = headers.get("x-real-ip")
            ua = headers.get("user-agent")
        if not ip:
            client = getattr(request, "client", None)
            if client and hasattr(client, "host"):
                ip = client.host
        return ip, ua

    # ------------------------------------------------------------
    # POST /account/settings/personal — update personal info
    # ------------------------------------------------------------
    @http_api.post("/account/settings/personal", response_class=http_api.HTMLResponse)
    async def update_personal(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return redirect

        try:
            allowed = await db_service.has_access(user_id, "account.profile.edit")
        except Exception:
            allowed = False

        if not allowed:
            return _redirect(request, "error", "personal", "no_permission")

        form = await request.form()
        data = {
            "first_name":    (form.get("first_name")    or "").strip(),
            "last_name":     (form.get("last_name")     or "").strip(),
            "national_code": (form.get("national_code") or "").strip() or None,
            "birth_date":    (form.get("birth_date")    or "").strip() or None,
            "gender":        (form.get("gender")        or "").strip() or None,
        }

        try:
            ok = await db_service.update_personal_info(user_id, data)
        except Exception as exc:
            if logger:
                logger.log(f"update_personal failed: {exc}", level="ERROR", tag="settings")
            ok = False

        if ok:
            await _refresh_session(request, user_id)
            return _redirect(request, "success", "personal")
        return _redirect(request, "error", "personal", "update_failed")

    # ------------------------------------------------------------
    # POST /account/settings/contact — update contact info
    # ------------------------------------------------------------
    @http_api.post("/account/settings/contact", response_class=http_api.HTMLResponse)
    async def update_contact(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return redirect

        try:
            allowed = await db_service.has_access(user_id, "account.profile.edit")
        except Exception:
            allowed = False

        if not allowed:
            return _redirect(request, "error", "contact", "no_permission")

        form = await request.form()
        data = {
            "email":          (form.get("email")          or "").strip() or None,
            "phone":          (form.get("phone")          or "").strip() or None,
            "address_line1":  (form.get("address_line1")  or "").strip() or None,
            "address_line2":  (form.get("address_line2")  or "").strip() or None,
            "city":           (form.get("city")           or "").strip() or None,
            "state_province": (form.get("state_province") or "").strip() or None,
            "postal_code":    (form.get("postal_code")    or "").strip() or None,
            "country":        (form.get("country")        or "").strip() or None,
        }

        try:
            ok = await db_service.update_contact_info(user_id, data)
        except Exception as exc:
            if logger:
                logger.log(f"update_contact failed: {exc}", level="ERROR", tag="settings")
            ok = False

        if ok:
            await _refresh_session(request, user_id)
            return _redirect(request, "success", "contact")
        return _redirect(request, "error", "contact", "update_failed")

    # ------------------------------------------------------------
    # POST /account/settings/password — change password
    # ------------------------------------------------------------
    @http_api.post("/account/settings/password", response_class=http_api.HTMLResponse)
    async def change_password(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return redirect

        try:
            allowed = await db_service.has_access(user_id, "account.password.change")
        except Exception:
            allowed = False

        if not allowed:
            return _redirect(request, "error", "password", "no_permission")

        form = await request.form()
        current = form.get("current_password") or ""
        new1    = form.get("new_password") or ""
        new2    = form.get("confirm_password") or ""

        if new1 != new2:
            return _redirect(request, "error", "password", "password_mismatch")

        ip, ua = _client_info(request)

        from app.db_manager.workflows import SettingsError

        try:
            await db_service.change_password(user_id, current, new1, ip, ua)
        except SettingsError as exc:
            return _redirect(request, "error", "password", exc.code)
        except Exception as exc:
            if logger:
                logger.log(f"change_password failed: {exc}", level="ERROR", tag="settings")
            return _redirect(request, "error", "password", "internal_error")

        return _redirect(request, "success", "password")

    # ------------------------------------------------------------
    # POST /account/settings/2fa/enable
    # ------------------------------------------------------------
    @http_api.post("/account/settings/2fa/enable", response_class=http_api.HTMLResponse)
    async def enable_2fa(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return redirect

        try:
            allowed = await db_service.has_access(user_id, "account.2fa.manage")
        except Exception:
            allowed = False

        if not allowed:
            return _redirect(request, "error", "2fa", "no_permission")

        # NOTE: The full TOTP setup flow (secret generation, QR code,
        # verification) will be added in a later task. For now, this
        # route is a placeholder that returns a "not yet available"
        # message so the UI can be wired without backend logic.
        return _redirect(request, "error", "2fa", "not_yet_available")

    # ------------------------------------------------------------
    # POST /account/settings/2fa/disable
    # ------------------------------------------------------------
    @http_api.post("/account/settings/2fa/disable", response_class=http_api.HTMLResponse)
    async def disable_2fa(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return redirect

        try:
            allowed = await db_service.has_access(user_id, "account.2fa.manage")
        except Exception:
            allowed = False

        if not allowed:
            return _redirect(request, "error", "2fa", "no_permission")

        ip, ua = _client_info(request)

        from app.db_manager.workflows import SettingsError

        try:
            await db_service.disable_2fa(user_id, ip, ua)
        except SettingsError as exc:
            return _redirect(request, "error", "2fa", exc.code)
        except Exception as exc:
            if logger:
                logger.log(f"disable_2fa failed: {exc}", level="ERROR", tag="settings")
            return _redirect(request, "error", "2fa", "internal_error")

        return _redirect(request, "success", "2fa")
