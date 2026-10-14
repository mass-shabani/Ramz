"""
Account Setting Routes

GET /account/settings — renders the authenticated user's settings page.
"""
from typing import Any
import re


# ============================================================
# Validation helpers
# ============================================================

# Conservative email regex.
#   - Local part: letters, digits, . _ % + -
#   - Domain:     letters, digits, . -
#   - TLD:        at least 2 letters
# This rejects inputs like "foo@bar" (no TLD) and "foo@bar.c" (1-char TLD).
EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?)*"
    r"\.[A-Za-z]{2,}$"
)

# Phone: optional leading "+", then digits, spaces, hyphens, parens, dots.
PHONE_ALLOWED_RE = re.compile(r"^\+?[0-9\s\-().]+$")


def is_valid_email(address: str) -> bool:
    """Return True if the string looks like a plausible email address."""
    if not isinstance(address, str):
        return False
    address = address.strip()
    if not address or len(address) > 254:
        return False
    return bool(EMAIL_RE.match(address))


def is_valid_phone(number: str) -> bool:
    """
    Return True if the string looks like a plausible phone number.

    Accepts international formats with digits, spaces, hyphens,
    parentheses, and an optional leading "+". Requires between 7
    and 20 digits total.
    """
    if not isinstance(number, str):
        return False
    number = number.strip()
    if not number or not PHONE_ALLOWED_RE.match(number):
        return False
    digits = sum(1 for c in number if c.isdigit())
    return 7 <= digits <= 20


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
        # Full session guard
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return redirect

        # Re-fetch current_user after guard (session may have been cleared)
        current_user = request.session.get("user")

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
        Return (user_id, None) on success.
        Return (None, response) if the request should be redirected or
        rejected (revoked/disabled session).

        The type of response depends on whether this is an AJAX request:
            • AJAX → 401 JSON with status="session_revoked"
            • HTML → 302 redirect to "/"
        """
        current_user = (
            request.session.get("user")
            if hasattr(request, "session")
            else None
        )

        def _is_ajax():
            headers = getattr(request, "headers", None)
            if not headers:
                return False
            accept = headers.get("accept", "") or ""
            xrw = headers.get("x-requested-with", "") or ""
            return ("application/json" in accept.lower()
                    or "xmlhttprequest" in xrw.lower())

        def _reject(reason):
            try:
                request.session.clear()
            except Exception:
                pass
            if _is_ajax():
                return None, http_api.JSONResponse(
                    content={
                        "status": "session_revoked",
                        "message": "Your session is no longer valid.",
                        "reason": reason,
                    },
                    status_code=401,
                )
            return None, http_api.RedirectResponse(url="/", status_code=302)

        if not current_user:
            if _is_ajax():
                return None, http_api.JSONResponse(
                    content={
                        "status": "session_revoked",
                        "message": "Not signed in.",
                        "reason": "no_user",
                    },
                    status_code=401,
                )
            return None, http_api.RedirectResponse(
                url="/login", status_code=302
            )

        user_id = (
            current_user.get("user_id")
            if isinstance(current_user, dict)
            else None
        )
        if not user_id:
            return _reject("no_user_id")

        # 1. Enabled check
        try:
            enabled = await db_service.is_user_enabled(user_id)
        except Exception:
            enabled = True

        if not enabled:
            if logger:
                logger.log(
                    f"Session invalidated for user_id={user_id} (disabled)",
                    level="WARNING", tag="settings",
                )
            return _reject("disabled")

        # 2. Revoked session check
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
                if logger:
                    logger.log(
                        f"Session revoked for user_id={user_id}",
                        level="WARNING", tag="settings",
                    )
                return _reject("revoked")

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

    async def _require_password(form, user_id):
        """
        Verify that the password field in `form` matches the current
        user's stored password.

        Returns None on success, or a JSON error response on failure.
        """
        password = (form.get("password") or "").strip()
        if not password:
            return _json_error(
                "password_required",
                "Please enter your password to confirm this action."
            )

        try:
            ok = await db_service.verify_current_user_password(user_id, password)
        except Exception:
            ok = False

        if not ok:
            return _json_error(
                "invalid_password",
                "The password you entered is incorrect. "
                "The action was not performed."
            )

        return None

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
        if not is_valid_email(address):
            return _json_error(
                "invalid_email",
                "Please enter a valid email address (e.g. you@example.com)."
            )

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

        return _json_ok(
            "Email added.",
            section="contact",
            reload_section=True,   # force partial reload so the list updates
        )

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
        if not is_valid_phone(number):
            return _json_error(
                "invalid_phone",
                "Please enter a valid phone number (7–20 digits, "
                "optional leading +, spaces and hyphens allowed)."
            )

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

        return _json_ok(
            "Phone number added.",
            section="contact",
            reload_section=True,   # force partial reload so the list updates
        )

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
    # Address management (no primary concept)
    # ------------------------------------------------------------
    @http_api.post("/account/settings/addresses/add",
                   response_class=http_api.HTMLResponse)
    async def add_address(request: http_api.Request):
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
        line1 = (form.get("address_line1") or "").strip()
        if not line1:
            return _json_error("invalid_data", "Street address is required.")

        try:
            ok = await db_service.add_address(
                user_id,
                address_line1=line1,
                address_line2=(form.get("address_line2") or "").strip() or None,
                city=(form.get("city") or "").strip() or None,
                state_province=(form.get("state_province") or "").strip() or None,
                postal_code=(form.get("postal_code") or "").strip() or None,
                country=(form.get("country") or "Iran").strip(),
                address_type=(form.get("address_type") or "home").strip(),
            )
        except Exception as exc:
            if logger:
                logger.log(f"add_address failed: {exc}", level="ERROR", tag="settings")
            ok = False

        if not ok:
            return _json_error("add_failed", "Could not add address.")

        return _json_ok(
            "Address added.",
            section="contact",
            reload_section=True,
        )

    @http_api.post("/account/settings/addresses/update",
                   response_class=http_api.HTMLResponse)
    async def update_address(request: http_api.Request):
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
            address_id = int(form.get("address_id") or 0)
        except ValueError:
            address_id = 0
        if not address_id:
            return _json_error("invalid_data", "Missing address ID.")

        line1 = (form.get("address_line1") or "").strip()
        if not line1:
            return _json_error("invalid_data", "Street address is required.")

        data = {
            "address_line1":  line1,
            "address_line2":  (form.get("address_line2") or "").strip() or None,
            "city":           (form.get("city") or "").strip() or None,
            "state_province": (form.get("state_province") or "").strip() or None,
            "postal_code":    (form.get("postal_code") or "").strip() or None,
            "country":        (form.get("country") or "Iran").strip(),
            "address_type":   (form.get("address_type") or "home").strip(),
        }

        try:
            ok = await db_service.update_address(user_id, address_id, data)
        except Exception:
            ok = False

        if not ok:
            return _json_error("update_failed", "Could not update address.")

        return _json_ok(
            "Address updated.",
            section="contact",
            reload_section=True,
        )

    @http_api.post("/account/settings/addresses/delete",
                   response_class=http_api.HTMLResponse)
    async def delete_address(request: http_api.Request):
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
            address_id = int(form.get("address_id") or 0)
        except ValueError:
            address_id = 0
        if not address_id:
            return _json_error("invalid_data", "Missing address ID.")

        try:
            ok = await db_service.remove_address(user_id, address_id)
        except Exception:
            ok = False

        if not ok:
            return _json_error("cannot_remove", "Could not remove this address.")

        return _json_ok(
            "Address removed.",
            section="contact",
            reload_section=True,
        )

    # ------------------------------------------------------------
    # Bank accounts
    # ------------------------------------------------------------
    @http_api.post("/account/settings/banking/accounts/add",
                   response_class=http_api.HTMLResponse)
    async def add_bank_account(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.banking.manage")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()

        err = await _require_password(form, user_id)
        if err:
            return err

        bank_id_str = (form.get("bank_id") or "").strip()
        account_number = (form.get("account_number") or "").strip()
        account_name = (form.get("account_name") or "").strip()
        iban = (form.get("iban") or "").strip() or None

        try:
            bank_id = int(bank_id_str)
        except ValueError:
            bank_id = 0

        if not bank_id or not account_number or not account_name:
            return _json_error("invalid_data", "Bank, account number and account name are required.")

        try:
            ok = await db_service.add_bank_account(
                user_id, bank_id, account_number, account_name, iban
            )
        except Exception as exc:
            if logger:
                logger.log(f"add_bank_account failed: {exc}", level="ERROR", tag="settings")
            ok = False

        if not ok:
            return _json_error("add_failed", "Could not add bank account.")

        return _json_ok("Bank account added.", section="banking", reload_section=True)

    @http_api.post("/account/settings/banking/accounts/update",
                   response_class=http_api.HTMLResponse)
    async def update_bank_account(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.banking.manage")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()

        err = await _require_password(form, user_id)
        if err:
            return err

        try:
            account_id = int(form.get("account_id") or 0)
        except ValueError:
            account_id = 0
        if not account_id:
            return _json_error("invalid_data", "Missing account ID.")

        try:
            bank_id = int(form.get("bank_id") or 0)
        except ValueError:
            bank_id = 0

        data = {
            "bank_id":        bank_id or None,
            "account_number": (form.get("account_number") or "").strip(),
            "account_name":   (form.get("account_name") or "").strip(),
            "iban":           (form.get("iban") or "").strip() or None,
        }
        # Remove empty account_number/account_name from update (not allowed)
        if not data["account_number"]:
            return _json_error("invalid_data", "Account number is required.")
        if not data["account_name"]:
            return _json_error("invalid_data", "Account name is required.")
        if not data["bank_id"]:
            data.pop("bank_id")

        try:
            ok = await db_service.update_bank_account(user_id, account_id, data)
        except Exception:
            ok = False

        if not ok:
            return _json_error("update_failed", "Could not update bank account.")

        return _json_ok("Bank account updated.", section="banking", reload_section=True)

    @http_api.post("/account/settings/banking/accounts/delete",
                   response_class=http_api.HTMLResponse)
    async def delete_bank_account(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.banking.manage")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()

        err = await _require_password(form, user_id)
        if err:
            return err

        try:
            account_id = int(form.get("account_id") or 0)
        except ValueError:
            account_id = 0
        if not account_id:
            return _json_error("invalid_data", "Missing account ID.")

        try:
            ok, reason = await db_service.remove_bank_account(user_id, account_id)
        except Exception:
            ok, reason = False, "not_found"

        if not ok:
            if reason == "has_cards":
                return _json_error(
                    "has_cards",
                    "This bank account still has cards. "
                    "Please remove all cards first, then delete the account."
                )
            return _json_error("cannot_remove", "Could not remove this bank account.")

        return _json_ok("Bank account removed.", section="banking", reload_section=True)

    # ------------------------------------------------------------
    # Bank cards
    # ------------------------------------------------------------
    @http_api.post("/account/settings/banking/cards/add",
                   response_class=http_api.HTMLResponse)
    async def add_bank_card(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.banking.manage")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()

        err = await _require_password(form, user_id)
        if err:
            return err

        try:
            account_id = int(form.get("account_id") or 0)
        except ValueError:
            account_id = 0
        card_number = (form.get("card_number") or "").strip().replace(" ", "").replace("-", "")
        card_holder = (form.get("card_holder_name") or "").strip()
        expiry = (form.get("expiry_date") or "").strip() or None

        if not account_id or not card_number or not card_holder:
            return _json_error("invalid_data", "Account, card number and holder name are required.")

        if not (13 <= len(card_number) <= 19) or not card_number.isdigit():
            return _json_error("invalid_card", "Card number must be 13–19 digits.")

        try:
            ok = await db_service.add_bank_card(
                user_id, account_id, card_number, card_holder, expiry
            )
        except Exception as exc:
            if logger:
                logger.log(f"add_bank_card failed: {exc}", level="ERROR", tag="settings")
            ok = False

        if not ok:
            return _json_error("add_failed", "Could not add card. It may already be registered.")

        return _json_ok("Card added.", section="banking", reload_section=True)

    @http_api.post("/account/settings/banking/cards/update",
                   response_class=http_api.HTMLResponse)
    async def update_bank_card(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.banking.manage")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()

        err = await _require_password(form, user_id)
        if err:
            return err

        try:
            card_id = int(form.get("card_id") or 0)
        except ValueError:
            card_id = 0
        if not card_id:
            return _json_error("invalid_data", "Missing card ID.")

        card_number = (form.get("card_number") or "").strip().replace(" ", "").replace("-", "")
        card_holder = (form.get("card_holder_name") or "").strip()
        expiry = (form.get("expiry_date") or "").strip() or None

        if not card_number or not card_holder:
            return _json_error("invalid_data", "Card number and holder name are required.")

        if not (13 <= len(card_number) <= 19) or not card_number.isdigit():
            return _json_error("invalid_card", "Card number must be 13–19 digits.")

        data = {
            "card_number":      card_number,
            "card_holder_name": card_holder,
            "expiry_date":      expiry,
        }

        try:
            ok = await db_service.update_bank_card(user_id, card_id, data)
        except Exception:
            ok = False

        if not ok:
            return _json_error("update_failed", "Could not update card.")

        return _json_ok("Card updated.", section="banking", reload_section=True)

    @http_api.post("/account/settings/banking/cards/delete",
                   response_class=http_api.HTMLResponse)
    async def delete_bank_card(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.banking.manage")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()

        err = await _require_password(form, user_id)
        if err:
            return err

        try:
            card_id = int(form.get("card_id") or 0)
        except ValueError:
            card_id = 0
        if not card_id:
            return _json_error("invalid_data", "Missing card ID.")

        try:
            ok = await db_service.remove_bank_card(user_id, card_id)
        except Exception:
            ok = False

        if not ok:
            return _json_error("cannot_remove", "Could not remove this card.")

        return _json_ok("Card removed.", section="banking", reload_section=True)

    # ------------------------------------------------------------
    # Banking — enable/disable
    # ------------------------------------------------------------
    @http_api.post("/account/settings/banking/accounts/toggle",
                   response_class=http_api.HTMLResponse)
    async def toggle_bank_account(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.banking.manage")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()

        err = await _require_password(form, user_id)
        if err:
            return err

        try:
            account_id = int(form.get("account_id") or 0)
        except ValueError:
            account_id = 0
        if not account_id:
            return _json_error("invalid_data", "Missing account ID.")

        enabled_str = (form.get("enabled") or "").strip().lower()
        enabled = enabled_str in ("1", "true", "yes")

        cascade_str = (form.get("cascade_cards") or "").strip().lower()
        cascade = cascade_str in ("1", "true", "yes")

        try:
            ok = await db_service.set_bank_account_enabled(
                user_id, account_id, enabled, cascade
            )
        except Exception:
            ok = False

        if not ok:
            return _json_error("update_failed", "Could not update account status.")

        action = "enabled" if enabled else "disabled"
        msg = f"Bank account {action}."
        if cascade:
            msg += " All cards were updated too."

        return _json_ok(msg, section="banking", reload_section=True)

    # ------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------
    @http_api.post("/account/settings/sessions/revoke",
                   response_class=http_api.HTMLResponse)
    async def revoke_session(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.sessions.manage")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()

        err = await _require_password(form, user_id)
        if err:
            return err

        target_session_id = (form.get("session_id") or "").strip()
        if not target_session_id:
            return _json_error("invalid_data", "Missing session ID.")

        current_session_id = request.session.get("session_id")
        if target_session_id == current_session_id:
            return _json_error(
                "is_current",
                "You cannot revoke your current session from here. "
                "Use Log Out instead."
            )

        try:
            target = await db_service.get_session(target_session_id)
        except Exception:
            target = None
        if not target or int(target.get("user_id", 0)) != user_id:
            return _json_error("not_found", "Session not found.")

        try:
            ok = await db_service.revoke_session(target_session_id)
        except Exception:
            ok = False

        if not ok:
            return _json_error("revoke_failed", "Could not revoke this session.")

        return _json_ok(
            "Session revoked.",
            section="sessions",
            reload_section=True,
        )

    @http_api.post("/account/settings/sessions/revoke-others",
                   response_class=http_api.HTMLResponse)
    async def revoke_other_sessions(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.sessions.manage")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()

        err = await _require_password(form, user_id)
        if err:
            return err

        current_session_id = request.session.get("session_id")

        try:
            await db_service.revoke_all_sessions(
                user_id, except_session_id=current_session_id
            )
        except Exception:
            return _json_error("revoke_failed", "Could not revoke other sessions.")

        return _json_ok(
            "All other sessions have been revoked.",
            section="sessions",
            reload_section=True,
        )

    @http_api.post("/account/settings/banking/cards/toggle",
                   response_class=http_api.HTMLResponse)
    async def toggle_bank_card(request: http_api.Request):
        user_id, redirect = await _ensure_authenticated(request)
        if redirect:
            return _json_error("unauthorized", "Session expired.")

        try:
            allowed = await db_service.has_access(user_id, "account.banking.manage")
        except Exception:
            allowed = False
        if not allowed:
            return _json_error("no_permission", "You do not have permission.")

        form = await request.form()

        err = await _require_password(form, user_id)
        if err:
            return err

        try:
            card_id = int(form.get("card_id") or 0)
        except ValueError:
            card_id = 0
        if not card_id:
            return _json_error("invalid_data", "Missing card ID.")

        enabled_str = (form.get("enabled") or "").strip().lower()
        enabled = enabled_str in ("1", "true", "yes")

        try:
            ok = await db_service.set_bank_card_enabled(user_id, card_id, enabled)
        except Exception:
            ok = False

        if not ok:
            return _json_error("update_failed", "Could not update card status.")

        action = "enabled" if enabled else "disabled"
        return _json_ok(
            f"Card {action}.",
            section="banking",
            reload_section=True,
        )

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
            # _ensure_authenticated already returns JSON for AJAX, plain redirect for HTML
            # If redirect is a 401 HTMLResponse, normalize to JSON for consistency
            if hasattr(redirect, 'status_code') and redirect.status_code == 401:
                return http_api.JSONResponse(
                    content={"status": "session_revoked", "message": "Session expired."},
                    status_code=401,
                )
            return redirect

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
        elif section == "banking":
            try:
                extra_context["bank_accounts"] = await db_service.list_bank_accounts(user_id)
            except Exception:
                extra_context["bank_accounts"] = []
            try:
                extra_context["banks"] = await db_service.list_banks()
            except Exception:
                extra_context["banks"] = []

        elif section == "sessions":
            try:
                extra_context["sessions"] = await db_service.list_active_sessions(user_id)
            except Exception:
                extra_context["sessions"] = []
            extra_context["current_session_id"] = request.session.get("session_id")

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

