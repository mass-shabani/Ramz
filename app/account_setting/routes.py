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
        # Extract query params
        qp = getattr(request, "query_params", {}) or {}
        flash_status  = qp.get("status")
        flash_section = qp.get("section")
        flash_code    = qp.get("code")

        # Which section is active — used as initial partial endpoint
        VALID_SECTIONS = {
            "personal", "contact", "password", "twofa",
            "subscription", "banking", "sessions", "danger",
        }
        requested_section = qp.get("section") or "personal"
        if requested_section not in VALID_SECTIONS:
            requested_section = "personal"

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
                    "section":       requested_section,
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

    def _wants_json(request):
        """Return True if the request explicitly accepts JSON."""
        headers = getattr(request, "headers", None)
        if not headers:
            return False
        accept = headers.get("accept", "") or ""
        return "application/json" in accept.lower()

    def _json_ok(message, **extra):
        """Build a success JSON response."""
        data = {"status": "success", "message": message}
        data.update(extra)
        return http_api.JSONResponse(content=data, status_code=200)

    def _json_error(code, message, **extra):
        """Build an error JSON response."""
        data = {"status": "error", "code": code, "message": message}
        data.update(extra)
        return http_api.JSONResponse(content=data, status_code=200)

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
            if _wants_json(request):
                return _json_error(
                    "no_permission",
                    "You do not have permission to perform this action.",
                    section="personal",
                )
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

            if _wants_json(request):
                # Fetch fresh profile to build the user_update payload
                try:
                    fresh = await db_service.get_full_profile(user_id)
                    user_update = {
                        "name":     fresh.full_name,
                        "initials": fresh.initials,
                        "email":    fresh.email,
                        "phone":    fresh.phone,
                    } if fresh else {}
                except Exception:
                    user_update = {}

                return _json_ok(
                    "Personal information updated.",
                    section="personal",
                    user_update=user_update,
                )

            return _redirect(request, "success", "personal")

        if _wants_json(request):
            return _json_error(
                "update_failed",
                "Failed to save personal information.",
                section="personal",
            )
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
            if _wants_json(request):
                return _json_error(
                    "no_permission",
                    "You do not have permission to perform this action.",
                    section="contact",
                )
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

            if _wants_json(request):
                try:
                    fresh = await db_service.get_full_profile(user_id)
                    user_update = {
                        "name":     fresh.full_name,
                        "initials": fresh.initials,
                        "email":    fresh.email,
                        "phone":    fresh.phone,
                    } if fresh else {}
                except Exception:
                    user_update = {}

                return _json_ok(
                    "Contact information updated.",
                    section="contact",
                    user_update=user_update,
                )

            return _redirect(request, "success", "contact")

        if _wants_json(request):
            return _json_error(
                "update_failed",
                "Failed to save contact information.",
                section="contact",
            )
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
            if _wants_json(request):
                return _json_error(
                    "no_permission",
                    "You do not have permission to change your password.",
                    section="password",
                )
            return _redirect(request, "error", "password", "no_permission")

        form = await request.form()
        current = form.get("current_password") or ""
        new1    = form.get("new_password") or ""
        new2    = form.get("confirm_password") or ""

        if new1 != new2:
            if _wants_json(request):
                return _json_error(
                    "password_mismatch",
                    "The two passwords do not match.",
                    section="password",
                )
            return _redirect(request, "error", "password", "password_mismatch")

        ip, ua = _client_info(request)

        from app.db_manager.workflows import SettingsError

        try:
            await db_service.change_password(user_id, current, new1, ip, ua)
        except SettingsError as exc:
            code = exc.code
            messages = {
                "invalid_password": "The current password is incorrect.",
                "weak_password":    "Password must be at least 8 characters.",
                "same_password":    "The new password is the same as the current one.",
                "user_not_found":   "User not found.",
                "internal_error":   "Something went wrong. Please try again.",
            }
            if _wants_json(request):
                return _json_error(
                    code,
                    messages.get(code, "Password change failed."),
                    section="password",
                )
            return _redirect(request, "error", "password", code)
        except Exception as exc:
            if logger:
                logger.log(f"change_password failed: {exc}", level="ERROR", tag="settings")
            if _wants_json(request):
                return _json_error(
                    "internal_error",
                    "Something went wrong. Please try again.",
                    section="password",
                )
            return _redirect(request, "error", "password", "internal_error")

        if _wants_json(request):
            return _json_ok(
                "Your password has been changed.",
                section="password",
            )
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
            if _wants_json(request):
                return _json_error(
                    "no_permission",
                    "You do not have permission to manage 2FA.",
                    section="twofa",
                )
            return _redirect(request, "error", "2fa", "no_permission")

        # NOTE: The full TOTP setup flow (secret generation, QR code,
        # verification) will be added in a later task. For now, this
        # route is a placeholder that returns a "not yet available"
        # message so the UI can be wired without backend logic.
        if _wants_json(request):
            return _json_error(
                "not_yet_available",
                "This feature will be available in a future update.",
                section="twofa",
            )
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
            if _wants_json(request):
                return _json_error(
                    "no_permission",
                    "You do not have permission to manage 2FA.",
                    section="twofa",
                )
            return _redirect(request, "error", "2fa", "no_permission")

        ip, ua = _client_info(request)

        from app.db_manager.workflows import SettingsError

        try:
            await db_service.disable_2fa(user_id, ip, ua)
        except SettingsError as exc:
            messages = {
                "2fa_not_enabled": "Two-factor authentication is not currently enabled.",
                "user_not_found":  "User not found.",
                "internal_error":  "Something went wrong. Please try again.",
            }
            if _wants_json(request):
                return _json_error(
                    exc.code,
                    messages.get(exc.code, "Could not disable 2FA."),
                    section="twofa",
                )
            return _redirect(request, "error", "2fa", exc.code)
        except Exception as exc:
            if logger:
                logger.log(f"disable_2fa failed: {exc}", level="ERROR", tag="settings")
            if _wants_json(request):
                return _json_error(
                    "internal_error",
                    "Something went wrong. Please try again.",
                    section="twofa",
                )
            return _redirect(request, "error", "2fa", "internal_error")

        if _wants_json(request):
            return _json_ok(
                "Two-factor authentication has been disabled.",
                section="twofa",
                reload_section=True,
            )
        return _redirect(request, "success", "2fa")

    # ------------------------------------------------------------
    # Email management
    # ------------------------------------------------------------
    @http_api.post("/account/settings/emails/add",
                   response_class=http_api.HTMLResponse)
    async def add_email(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.profile.edit")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()
        address = (form.get("email_address") or "").strip()
        if not address or "@" not in address:
            return _json_error("invalid_email", "Please enter a valid email address.")

        try:
            ok = await db_service.add_email(user_id, address)
        except Exception as exc:
            if logger:
                logger.log(f"add_email failed: {exc}", level="ERROR", tag="settings")
            ok = False

        if not ok:
            return _json_error(
                "email_exists",
                "This email is already registered."
            )

        return _json_ok("Email added.", section="contact")

    @http_api.post("/account/settings/emails/set-primary",
                   response_class=http_api.HTMLResponse)
    async def set_primary_email(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.profile.edit")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()
        try:
            email_id = int(form.get("email_id") or 0)
        except ValueError:
            email_id = 0
        if not email_id:
            return _json_error("invalid_data", "Missing email ID.")

        try:
            ok = await db_service.set_primary_email(user_id, email_id)
        except Exception:
            ok = False

        if not ok:
            return _json_error("update_failed", "Could not set primary email.")

        await _refresh_session(request, user_id)
        return _json_ok("Primary email updated.", section="contact")

    @http_api.post("/account/settings/emails/delete",
                   response_class=http_api.HTMLResponse)
    async def delete_email(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.profile.edit")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()
        try:
            email_id = int(form.get("email_id") or 0)
        except ValueError:
            email_id = 0
        if not email_id:
            return _json_error("invalid_data", "Missing email ID.")

        try:
            ok, reason = await db_service.remove_email(user_id, email_id)
        except Exception:
            ok, reason = False, "not_found"

        if not ok:
            if reason == "is_primary":
                return _json_error(
                    "cannot_remove",
                    "This is your primary email. Set another email as primary first."
                )
            if reason == "is_last":
                return _json_error(
                    "cannot_remove",
                    "You cannot remove the last remaining email."
                )
            return _json_error("cannot_remove", "Could not remove this email.")

        return _json_ok("Email removed.", section="contact")

    # ------------------------------------------------------------
    # Phone management
    # ------------------------------------------------------------
    @http_api.post("/account/settings/phones/add",
                   response_class=http_api.HTMLResponse)
    async def add_phone(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.profile.edit")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()
        number = (form.get("phone_number") or "").strip()
        phone_type = (form.get("phone_type") or "mobile").strip()
        if not number:
            return _json_error("invalid_data", "Please enter a phone number.")

        try:
            ok = await db_service.add_phone(user_id, number, phone_type)
        except Exception as exc:
            if logger:
                logger.log(f"add_phone failed: {exc}", level="ERROR", tag="settings")
            ok = False

        if not ok:
            return _json_error(
                "phone_exists",
                "This phone number is already registered."
            )

        return _json_ok("Phone number added.", section="contact")

    @http_api.post("/account/settings/phones/set-primary",
                   response_class=http_api.HTMLResponse)
    async def set_primary_phone(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.profile.edit")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()
        try:
            phone_id = int(form.get("phone_id") or 0)
        except ValueError:
            phone_id = 0
        if not phone_id:
            return _json_error("invalid_data", "Missing phone ID.")

        try:
            ok = await db_service.set_primary_phone(user_id, phone_id)
        except Exception:
            ok = False

        if not ok:
            return _json_error("update_failed", "Could not set primary phone.")

        await _refresh_session(request, user_id)
        return _json_ok("Primary phone updated.", section="contact")

    @http_api.post("/account/settings/phones/delete",
                   response_class=http_api.HTMLResponse)
    async def delete_phone(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.profile.edit")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()
        try:
            phone_id = int(form.get("phone_id") or 0)
        except ValueError:
            phone_id = 0
        if not phone_id:
            return _json_error("invalid_data", "Missing phone ID.")

        try:
            ok, reason = await db_service.remove_phone(user_id, phone_id)
        except Exception:
            ok, reason = False, "not_found"

        if not ok:
            if reason == "is_primary":
                return _json_error(
                    "cannot_remove",
                    "This is your primary phone. Set another phone as primary first."
                )
            if reason == "is_last":
                return _json_error(
                    "cannot_remove",
                    "You cannot remove the last remaining phone."
                )
            return _json_error("cannot_remove", "Could not remove this phone.")

        return _json_ok("Phone number removed.", section="contact")

    # ------------------------------------------------------------
    # POST /account/settings/partials/{section} — partial loader
    # ------------------------------------------------------------
    PARTIAL_TEMPLATES = {
        "personal":     "partials/personal.html",
        "contact":      "partials/contact.html",
        "password":     "partials/password.html",
        "twofa":        "partials/twofa.html",
        "subscription": "partials/subscription.html",
        "banking":      "partials/banking.html",
        "sessions":     "partials/sessions.html",
        "danger":       "partials/danger.html",
    }

    @http_api.post("/account/settings/partials/{section}",
                   response_class=http_api.HTMLResponse)
    async def settings_partial(request: http_api.Request, section: str):
        """
        Return the HTML fragment for a specific settings section.
        Called by <content-container> when a nav item is clicked.
        """
        # Auth guards
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return http_api.HTMLResponse(
                content="<div class='card'><p>Session expired.</p></div>",
                status_code=401,
            )

        # Validate section
        template_name = PARTIAL_TEMPLATES.get(section)
        if not template_name:
            return http_api.HTMLResponse(
                content="<div class='card'><p>Section not available.</p></div>",
                status_code=404,
            )

        # Load profile
        try:
            profile = await db_service.get_full_profile(user_id)
        except Exception:
            profile = None

        if profile is None:
            return http_api.HTMLResponse(
                content="<div class='card'><p>Profile not found.</p></div>",
                status_code=404,
            )

        # Compute permissions
        async def _has(form_id):
            try:
                return await db_service.has_access(user_id, form_id)
            except Exception:
                return False

        permissions = {
            "profile_edit": await _has("account.profile.edit"),
            "password":     await _has("account.password.change"),
            "twofa":        await _has("account.2fa.manage"),
            "banking":      await _has("account.banking.manage"),
            "sessions":     await _has("account.sessions.manage"),
            "delete":       await _has("account.delete"),
        }

        # Additional context for the contact section
        extra_context = {}
        if section == "contact":
            try:
                extra_context["channels"] = await db_service.list_contact_channels(user_id)
            except Exception:
                extra_context["channels"] = {
                    "emails": [], "phones": [], "addresses": []
                }

        # Render
        try:
            html = await template_service.render(
                template_name,
                context={
                    "profile":     profile,
                    "permissions": permissions,
                    "section":     section,
                    "module_name": "account_setting",
                    **extra_context,
                },
            )
            return http_api.HTMLResponse(content=html)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Error rendering settings partial '{section}': {exc}",
                    level="ERROR",
                    tag="settings",
                )
            return http_api.HTMLResponse(
                content="<div class='card'><p>Failed to load section.</p></div>",
                status_code=500,
            )

