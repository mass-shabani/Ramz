"""
routes — settings UI for crypto_providers (account_setting extension).

All endpoints live under `/settings/crypto/providers/`. They are
discovered by `content-container` in account_setting via the
`ui.account_setting.sections` extension registered in module.py.

Endpoints
---------
    POST /settings/crypto/providers/partials/overview
        HTML partial: list of configurable providers + per-user status.
        Rendered from templates/partials/overview.html (TASK 78.9).

    POST /settings/crypto/providers/partials/nobitex
        HTML partial: Nobitex API key + secret form.
        Rendered from templates/partials/nobitex.html (TASK 78.9).

    POST /settings/crypto/providers/save
        JSON: encrypt and store credentials for one provider.

    POST /settings/crypto/providers/test
        JSON: verify stored credentials can be decrypted.

Auth
----
Every endpoint requires:
    1. A valid session (session cookie + enabled + not revoked).
    2. The `crypto.credentials.manage` grant.

Mutations (save, test) also require the user's current password
(mirrors admin_panel mutation pattern). Password verification uses
`db_service.verify_current_user_password(user_id, password)`.

Design
------
The helper functions (`_ensure_authenticated`, `_check_access`,
`_parse_body`, `_json_error`) deliberately duplicate code from
`crypto_market/routes.py` and `account_setting/routes.py`. Cross-
module import of private helpers is forbidden by the project's
"no cross-module imports" rule; copying is the authorized pattern
(see crypto_market/routes.py for the same duplication rationale).

The `test` endpoint is a STUB in the sense that it only verifies
decryption succeeds. It does NOT call the provider's API — that
requires authenticated endpoints that arrive with the future
crypto_trading module. The TODO is explicit in the endpoint body.
"""
from typing import Any, Optional


# --------------------------------------------------------------
# Provider catalog (configurable providers in this phase)
# --------------------------------------------------------------
# A provider is "configurable" if it requires user-provided
# credentials. Public providers (CoinGecko, FX) are omitted.
CONFIGURABLE_PROVIDERS = [
    {
        "id": "nobitex",
        "name": "Nobitex",
        "description": (
            "Iranian crypto exchange. Required for authenticated "
            "operations (orders, wallet). Public market data is "
            "already available without credentials."
        ),
        "credential_fields": ["api_key", "api_secret"],
        "endpoint": "/settings/crypto/providers/partials/nobitex",
    },
]


# --------------------------------------------------------------
# Auth helpers
# --------------------------------------------------------------
async def _ensure_authenticated(request, db_service, logger):
    """
    Session + enabled + revoked checks.

    Returns (session_id, user_id) on success, (None, None) on failure.
    Mirrors account_setting/routes.py::_ensure_authenticated.

    Fail-open on transient DB errors: a DB hiccup must not eject
    every user from the settings page.
    """
    try:
        session_id = request.session.get("session_id")
    except Exception:
        session_id = None

    if not session_id:
        return None, None

    try:
        user_data = request.session.get("user") or {}
    except Exception:
        user_data = {}
    user_id = (
        user_data.get("user_id")
        if isinstance(user_data, dict) else None
    )
    if not user_id:
        return None, None

    if db_service is None:
        return session_id, int(user_id)

    try:
        enabled = await db_service.is_user_enabled(user_id)
        if not enabled:
            try:
                request.session.clear()
            except Exception:
                pass
            if logger:
                logger.log(
                    f"Session rejected (user_id={user_id} disabled)",
                    level="WARNING", tag="crypto_providers",
                )
            return None, None

        valid = await db_service.is_session_valid(session_id)
        if not valid:
            try:
                request.session.clear()
            except Exception:
                pass
            if logger:
                logger.log(
                    f"Session rejected (revoked, session_id="
                    f"{session_id[:8]}…)",
                    level="WARNING", tag="crypto_providers",
                )
            return None, None
    except Exception as exc:
        # Fail-open — see docstring.
        if logger:
            logger.log(
                f"Session check failed ({exc}); allowing request",
                level="WARNING", tag="crypto_providers",
            )

    return session_id, int(user_id)


async def _check_access(request, db_service, logger):
    """
    Grant check for `crypto.credentials.manage`.

    Returns (session_id, user_id, None) on success.
    Returns (None, None, error_dict) on failure.

    Fail-closed: any failure in `has_access` denies access (safer than
    silently granting admin operations). Mirrors the pattern in
    crypto_market/routes.py::_check_coins_access after the security
    fix in TASK 78.6-FIX.
    """
    session_id, user_id = await _ensure_authenticated(
        request, db_service, logger
    )
    if session_id is None or user_id is None:
        return None, None, {
            "status_code": 401,
            "body": {
                "status": "error",
                "code": "not_authenticated",
                "message": "Not signed in or session expired.",
            },
        }

    if db_service is None:
        if logger:
            logger.log(
                "db_service is None — cannot verify grant; "
                "denying access (fail-closed)",
                level="ERROR", tag="crypto_providers",
            )
        return None, None, {
            "status_code": 503,
            "body": {
                "status": "error",
                "code": "service_unavailable",
                "message": "Access control unavailable; try later.",
            },
        }

    try:
        allowed = await db_service.has_access(
            user_id, "crypto.credentials.manage"
        )
    except Exception as exc:
        if logger:
            logger.log(
                f"Grant check raised ({exc}); denying access "
                f"(fail-closed)",
                level="ERROR", tag="crypto_providers",
            )
        return None, None, {
            "status_code": 503,
            "body": {
                "status": "error",
                "code": "service_unavailable",
                "message": "Access control unavailable; try later.",
            },
        }

    if not allowed:
        return None, None, {
            "status_code": 403,
            "body": {
                "status": "error",
                "code": "no_permission",
                "message": (
                    "You do not have permission to manage "
                    "provider credentials."
                ),
            },
        }

    return session_id, user_id, None


# --------------------------------------------------------------
# Body parsing / response helpers
# --------------------------------------------------------------
async def _parse_body(request):
    """
    Parse request body, accepting BOTH JSON and form-encoded input.

    Two kinds of callers hit the save/test endpoints:

        • The settings UI form (see nobitex.html + settings.html JS).
          The JS builds a `FormData` and calls fetch(); the browser
          sends `Content-Type: multipart/form-data`.

        • API clients (curl, mobile apps, future integrations) that
          send `Content-Type: application/json`.

    Handling both is required so the same endpoint works for both
    callers. The dispatch is based on the Content-Type header —
    never on trying one parser and falling back to the other, which
    would hide real JSON errors.

    Returns (dict, None) on success, (None, error_dict) on failure.
    In all cases the returned dict is a plain dict of str→str/any.
    """

    content_type = (
        request.headers.get("content-type") or ""
    ).lower()

    # ---- JSON path (API clients, curl, future tests) -----------
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            return None, {
                "status_code": 400,
                "body": {
                    "status": "error",
                    "code": "invalid_body",
                    "message": "Request body must be valid JSON.",
                },
            }
        if body is None:
            return {}, None
        if not isinstance(body, dict):
            return None, {
                "status_code": 400,
                "body": {
                    "status": "error",
                    "code": "invalid_body",
                    "message": "Request body must be a JSON object.",
                },
            }
        return body, None

    # ---- Form-encoded path (browser form submit) --------------
    if (
        "multipart/form-data" in content_type
        or "application/x-www-form-urlencoded" in content_type
    ):
        try:
            form = await request.form()
        except Exception:
            return None, {
                "status_code": 400,
                "body": {
                    "status": "error",
                    "code": "invalid_body",
                    "message": "Malformed form data.",
                },
            }
        # `dict(form)` produces a dict[str, str | UploadFile].
        # Our forms never upload files, so values are strings.
        # Coerce to plain dict so callers can use `.get(...)`
        # uniformly regardless of the request kind.
        return dict(form), None

    # ---- No body or unknown content-type ----------------------
    # Treat as empty body. Endpoints that require fields will
    # reject with a specific "field_required" error.
    return {}, None


def _json_error(http_api, status_code: int, code: str, message: str):
    """Build a JSON error response."""
    return http_api.JSONResponse(
        content={
            "status": "error",
            "code":   code,
            "message": message,
        },
        status_code=status_code,
    )


def _get_provider_entry(provider_id: str) -> Optional[dict]:
    """Return the catalog entry for a configurable provider, or None."""
    if not provider_id:
        return None
    pid = provider_id.strip().lower()
    for entry in CONFIGURABLE_PROVIDERS:
        if entry["id"] == pid:
            return entry
    return None


# --------------------------------------------------------------
# Route registration
# --------------------------------------------------------------
def register_routes(
    http_api: Any,
    credentials_service: Any,
    db_service: Any,
    template_service: Any,
    logger: Any,
) -> None:
    """
    Register all crypto_providers settings routes.
    """

    # ----------------------------------------------------------
    # POST /settings/crypto/providers/partials/overview
    # ----------------------------------------------------------
    @http_api.post(
        "/settings/crypto/providers/partials/overview",
        response_class=http_api.HTMLResponse,
    )
    async def partials_overview(request: http_api.Request):
        """
        Render the provider list partial.

        The HTML is rendered from templates/partials/overview.html,
        added in TASK 78.9. Until then, template_service.render()
        returns a "Template Error: '...' not found" placeholder,
        which is a valid (if unhelpful) HTML response — the
        endpoint remains functional.
        """
        session_id, user_id, err = await _check_access(
            request, db_service, logger
        )
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        # Build context for the template
        providers_context = []
        user_credentials = (
            await credentials_service.list_providers(user_id)
            if credentials_service else []
        )
        for entry in CONFIGURABLE_PROVIDERS:
            providers_context.append({
                **entry,
                "configured": entry["id"] in user_credentials,
            })

        context = {
            "module_name": "crypto_providers",
            "providers":   providers_context,
            "current_user": request.session.get("user") or {},
        }

        if template_service is None:
            return http_api.HTMLResponse(
                content=(
                    "<div class='card'><p>"
                    "Template service unavailable."
                    "</p></div>"
                ),
                status_code=500,
            )

        try:
            html = await template_service.render(
                "partials/overview.html", context
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"overview template render failed: {exc}",
                    level="ERROR", tag="crypto_providers",
                )
            return http_api.HTMLResponse(
                content=(
                    "<div class='card'><p>"
                    "Failed to render providers overview."
                    "</p></div>"
                ),
                status_code=500,
            )
        return http_api.HTMLResponse(content=html)

    # ----------------------------------------------------------
    # POST /settings/crypto/providers/partials/nobitex
    # ----------------------------------------------------------
    @http_api.post(
        "/settings/crypto/providers/partials/nobitex",
        response_class=http_api.HTMLResponse,
    )
    async def partials_nobitex(request: http_api.Request):
        """
        Render the Nobitex credentials form partial.

        HTML is rendered from templates/partials/nobitex.html
        (TASK 78.9). Until then, template_service returns a
        "not found" placeholder. Endpoint remains functional.
        """
        session_id, user_id, err = await _check_access(
            request, db_service, logger
        )
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        # Do NOT pass plaintext credentials to the template. The
        # template shows only whether each field is configured, never
        # the value.
        existing = await credentials_service.get_credentials(
            user_id, "nobitex"
        ) or {}
        configured_fields = {
            field: (field in existing)
            for field in ("api_key", "api_secret")
        }

        context = {
            "module_name":       "crypto_providers",
            "provider_id":       "nobitex",
            "provider_name":     "Nobitex",
            "configured_fields": configured_fields,
            "all_configured":    all(configured_fields.values()),
            "current_user":      request.session.get("user") or {},
        }

        if template_service is None:
            return http_api.HTMLResponse(
                content=(
                    "<div class='card'><p>"
                    "Template service unavailable."
                    "</p></div>"
                ),
                status_code=500,
            )

        try:
            html = await template_service.render(
                "partials/nobitex.html", context
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"nobitex template render failed: {exc}",
                    level="ERROR", tag="crypto_providers",
                )
            return http_api.HTMLResponse(
                content=(
                    "<div class='card'><p>"
                    "Failed to render Nobitex form."
                    "</p></div>"
                ),
                status_code=500,
            )
        return http_api.HTMLResponse(content=html)

    # ----------------------------------------------------------
    # POST /settings/crypto/providers/save
    # ----------------------------------------------------------
    @http_api.post(
        "/settings/crypto/providers/save",
        response_class=http_api.JSONResponse,
    )
    async def save_credentials(request: http_api.Request):
        """
        Encrypt and store credentials for one provider.

        Body:
            {
                "provider":  "nobitex",
                "api_key":   "...",       // optional
                "api_secret": "..." | "",  // optional, empty = skip
                "password":  "..."         // user's own password
            }

        Empty string values are SKIPPED (see CredentialService
        docstring) — they mean "do not change that field", not
        "overwrite with empty".

        Response:
            Success: {"status": "success", "message": "...",
                      "saved_fields": ["api_key", ...]}
            Failure: {"status": "error", "code": "...", "message": "..."}
        """
        session_id, user_id, err = await _check_access(
            request, db_service, logger
        )
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        body, err = await _parse_body(request)
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        provider_id = str(body.get("provider") or "").strip().lower()
        provider_entry = _get_provider_entry(provider_id)
        if provider_entry is None:
            return _json_error(
                http_api, 400, "invalid_provider",
                f"Unknown provider: {provider_id!r}",
            )

        # Extract declared credential fields
        keys: dict[str, str] = {}
        for field in provider_entry["credential_fields"]:
            raw = body.get(field)
            if isinstance(raw, str) and raw.strip():
                keys[field] = raw

        if not keys:
            return _json_error(
                http_api, 400, "empty_fields",
                "At least one credential field must be provided.",
            )

        # Verify user's password
        password = body.get("password")
        if not isinstance(password, str) or not password:
            return _json_error(
                http_api, 400, "password_required",
                "Please enter your password to confirm.",
            )

        if db_service is None:
            return _json_error(
                http_api, 503, "service_unavailable",
                "Password verification unavailable.",
            )

        try:
            pw_ok = await db_service.verify_current_user_password(
                user_id, password
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"password verification raised: {exc}",
                    level="ERROR", tag="crypto_providers",
                )
            pw_ok = False

        if not pw_ok:
            return _json_error(
                http_api, 200, "invalid_password",
                "The password you entered is incorrect.",
            )

        # Save
        if credentials_service is None:
            return _json_error(
                http_api, 503, "service_unavailable",
                "Credentials service unavailable.",
            )

        try:
            ok, code = await credentials_service.save_credentials(
                user_id=user_id,
                provider=provider_id,
                keys=keys,
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"save_credentials raised: {exc}",
                    level="ERROR", tag="crypto_providers",
                )
            ok, code = False, "internal_error"

        if not ok:
            messages = {
                "invalid_input":   "Missing or invalid input.",
                "empty_keys":      "No non-empty credentials provided.",
                "key_unavailable": "Encryption key unavailable.",
                "encrypt_failed":  "Encryption failed.",
                "verify_failed":   "Encryption round-trip verification failed.",
                "store_failed":    "Failed to store credentials.",
            }
            return _json_error(
                http_api, 200, code or "internal_error",
                messages.get(code or "internal_error",
                             "Failed to save credentials."),
            )

        if logger:
            logger.log(
                f"Credentials saved for user_id={user_id}, "
                f"provider={provider_id!r}, "
                f"fields={sorted(keys.keys())}",
                tag="crypto_providers",
            )

        return http_api.JSONResponse(
            content={
                "status":       "success",
                "message":      f"Credentials saved for {provider_id}.",
                "saved_fields": sorted(keys.keys()),
                # Trigger a reload of the current partial so the UI
                # picks up updated `configured_fields` (green "Saved"
                # badges) and the freshly-cleared input fields. The
                # reload endpoint is provider-specific, so the client
                # cannot infer it from the active nav item.
                "reload_endpoint": (
                    f"/settings/crypto/providers/partials/{provider_id}"
                ),
            },
            status_code=200,
        )

    # ----------------------------------------------------------
    # POST /settings/crypto/providers/test
    # ----------------------------------------------------------
    @http_api.post(
        "/settings/crypto/providers/test",
        response_class=http_api.JSONResponse,
    )
    async def test_credentials(request: http_api.Request):
        """
        Verify stored credentials can be decrypted.

        STUB (TASK 78.8): this endpoint does NOT call the provider's
        API. It only confirms that:
            1. Credentials are stored for the provider.
            2. Decryption succeeds (key valid, no corruption).

        TODO (future): once crypto_trading implements authenticated
        endpoints, replace with a real provider-side ping that
        verifies the API key is recognized by Nobitex.

        Body:
            {
                "provider": "nobitex",
                "password": "..."   // user's own password
            }
        """
        session_id, user_id, err = await _check_access(
            request, db_service, logger
        )
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        body, err = await _parse_body(request)
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        provider_id = str(body.get("provider") or "").strip().lower()
        provider_entry = _get_provider_entry(provider_id)
        if provider_entry is None:
            return _json_error(
                http_api, 400, "invalid_provider",
                f"Unknown provider: {provider_id!r}",
            )

        password = body.get("password")
        if not isinstance(password, str) or not password:
            return _json_error(
                http_api, 400, "password_required",
                "Please enter your password to confirm.",
            )

        if db_service is None:
            return _json_error(
                http_api, 503, "service_unavailable",
                "Password verification unavailable.",
            )

        try:
            pw_ok = await db_service.verify_current_user_password(
                user_id, password
            )
        except Exception:
            pw_ok = False

        if not pw_ok:
            return _json_error(
                http_api, 200, "invalid_password",
                "The password you entered is incorrect.",
            )

        if credentials_service is None:
            return _json_error(
                http_api, 503, "service_unavailable",
                "Credentials service unavailable.",
            )

        try:
            creds = await credentials_service.get_credentials(
                user_id, provider_id
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"test: get_credentials raised: {exc}",
                    level="ERROR", tag="crypto_providers",
                )
            creds = None

        if not creds:
            return _json_error(
                http_api, 200, "no_credentials",
                f"No credentials stored for {provider_id}.",
            )

        expected = set(provider_entry["credential_fields"])
        missing = expected - set(creds.keys())
        if missing:
            return _json_error(
                http_api, 200, "missing_fields",
                f"Missing credential fields: {sorted(missing)}",
            )

        return http_api.JSONResponse(
            content={
                "status":  "success",
                "message": (
                    f"Credentials for {provider_id} decrypted "
                    f"successfully. (API call test arrives with "
                    f"crypto_trading module.)"
                ),
                "fields":  sorted(creds.keys()),
            },
            status_code=200,
        )


__all__ = ["register_routes", "CONFIGURABLE_PROVIDERS"]
