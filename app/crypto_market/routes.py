"""
routes — JSON API of the crypto_market module.

Endpoints (this task)
---------------------
    POST /crypto/presence/heartbeat
        Refresh a session's presence and merge declared kinds.
        Body (optional): {"kinds": ["coins", "charts"]}
        Response (200):  {"status": "success"}

    POST /crypto/presence/leave
        Remove a session entirely, or remove specific kinds from it.
        Body (optional): {"kinds": ["coins"]}
        Response (200):  {"status": "success"}

Endpoints (later tasks)
-----------------------
    POST /crypto/market/api/coins              — TASK 77.12
    POST /crypto/market/api/klines/{symbol}    — TASK 77.13

Design
------
Presence endpoints are lightweight. They do NOT touch providers and
do NOT trigger a refresh cycle. The poller's own loop is the only
consumer of presence state; it polls whenever presence > 0.

Authentication
--------------
All presence endpoints require a valid, enabled, non-revoked session
(mirrors the pattern used by user_panel and account_setting routes).
On failure, the client receives:

    401 {"status": "session_revoked", "message": ...}

so the global fetch interceptor in ui_components/main.js can eject
the client.

Error shape
-----------
Success:  {"status": "success", ...}
Failure:  {"status": "error", "code": "...", "message": "..."}

Failures use proper HTTP status codes:
    401 — not authenticated / session revoked
    400 — malformed body (bad JSON, kinds not a list, etc.)
    500 — internal error (from the service or an unexpected exception)
"""
from typing import Any, Optional

from .market_service.api import CryptoMarketService


# Maximum kinds accepted in one request. Prevents memory abuse from a
# single malicious client. The client's real list is tiny (≤ 3 kinds).
_MAX_KINDS_PER_REQUEST = 20


# --------------------------------------------------------------
# Auth helper (mirrors user_panel / account_setting)
# --------------------------------------------------------------
async def _ensure_authenticated(request, db_service, logger):
    """
    Return (session_id, None) if the request is from a valid session.
    Return (None, error_response) otherwise.

    Fail-open on transient DB errors: a DB hiccup must not break the
    UI's heartbeat loop.
    """
    # 1. Session cookie
    try:
        session_id = request.session.get("session_id")
    except Exception:
        session_id = None

    if not session_id:
        return None, _json_error(
            401, "not_authenticated",
            "Not signed in.",
        )

    # 2. User must still be enabled (DB check, cached ~15s)
    if db_service is not None:
        try:
            user_data = request.session.get("user") or {}
            user_id = (
                user_data.get("user_id")
                if isinstance(user_data, dict) else None
            )
            if user_id:
                enabled = await db_service.is_user_enabled(user_id)
                if not enabled:
                    try:
                        request.session.clear()
                    except Exception:
                        pass
                    if logger:
                        logger.log(
                            f"Presence rejected: user_id={user_id} "
                            f"is disabled",
                            level="WARNING", tag="crypto_market",
                        )
                    return None, _json_error(
                        401, "session_revoked",
                        "Your account is no longer active.",
                    )

            # 3. Session must not be revoked (DB check, cached ~15s)
            valid = await db_service.is_session_valid(session_id)
            if not valid:
                try:
                    request.session.clear()
                except Exception:
                    pass
                if logger:
                    logger.log(
                        f"Presence rejected: session_id="
                        f"{session_id[:8]}… is revoked",
                        level="WARNING", tag="crypto_market",
                    )
                return None, _json_error(
                    401, "session_revoked",
                    "Your session is no longer valid.",
                )
        except Exception as exc:
            # Fail-open — see docstring.
            if logger:
                logger.log(
                    f"Presence auth check failed ({exc}); "
                    f"allowing request",
                    level="WARNING", tag="crypto_market",
                )

    return session_id, None


async def _check_coins_access(
    request, db_service, logger
) -> tuple[Optional[int], Optional[dict]]:
    """
    Check whether the current session's user has `crypto.coins.view`.

    Returns:
        (user_id, None)       if the user has access.
        (None, error_dict)    otherwise (401 not_authenticated /
                                       403 no_permission).

    Note: this is separate from `_ensure_authenticated` because that
    helper is used by presence endpoints (which only need auth, not a
    specific grant). Grant checks are route-specific.

    Fail-open on transient DB errors (mirrors _ensure_authenticated):
    a DB hiccup must not lock users out of read-only market data.
    """
    user_data = {}
    try:
        user_data = request.session.get("user") or {}
    except Exception:
        user_data = {}

    user_id = (
        user_data.get("user_id")
        if isinstance(user_data, dict) else None
    )
    if not user_id:
        return None, {
            "status_code": 401,
            "body": {
                "status": "error",
                "code": "not_authenticated",
                "message": "Not signed in.",
            },
        }

    if db_service is None:
        # No DB access means we cannot verify grants. Fail-open
        # matches the rest of the codebase's resilience posture.
        return int(user_id), None

    try:
        allowed = await db_service.has_access(
            user_id, "crypto.coins.view"
        )
    except Exception as exc:
        if logger:
            logger.log(
                f"Grant check failed ({exc}); allowing request",
                level="WARNING", tag="crypto_market",
            )
        return int(user_id), None

    if not allowed:
        return None, {
            "status_code": 403,
            "body": {
                "status": "error",
                "code": "no_permission",
                "message": "You do not have access to crypto coins.",
            },
        }

    return int(user_id), None


# --------------------------------------------------------------
# Response helpers
# --------------------------------------------------------------
def _json_success(http_api, **extra):
    """Build a 200 success JSON response."""
    body = {"status": "success"}
    body.update(extra)
    return http_api.JSONResponse(content=body, status_code=200)


def _json_error(status_code: int, code: str, message: str):
    """
    Build a JSON error response. Deliberately does not import
    http_api — the caller binds it when registering routes. We
    construct a plain dict here and let the route wrap it.
    """
    # See `register_routes` below for the actual JSONResponse build.
    return {
        "status_code": status_code,
        "body": {
            "status": "error",
            "code": code,
            "message": message,
        },
    }


# --------------------------------------------------------------
# Body parsing
# --------------------------------------------------------------
async def _parse_body(request):
    """
    Parse JSON body with tolerance.

    Returns (body_dict, error_or_none). On bad JSON, error is a
    dict suitable for _json_error. On empty body, returns ({}, None).
    """
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


def _sanitize_kinds(raw: Optional[Any]) -> Optional[list[str]]:
    """
    Validate and normalize the `kinds` field.

    Returns:
        • None  — field was missing/None/empty → caller treats as "all".
        • list  — sanitized, deduplicated, order-preserved, capped.

    Note: `heartbeat()` treats kinds=None as "refresh only, no kinds
    added". `leave()` treats kinds=None as "remove the whole session".
    This is consistent with PresenceRegistry semantics.
    """
    if raw is None:
        return None
    if not isinstance(raw, list):
        return None
    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        item = item.strip()
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= _MAX_KINDS_PER_REQUEST:
            break
    return result or None


# --------------------------------------------------------------
# Serialization
# --------------------------------------------------------------
def _serialize_decimal(value) -> Optional[str]:
    """
    Serialize a Decimal to a JSON-safe string.

    Returns None on invalid input (defensive — provider data should
    always be valid Decimal, but bad data must not crash the endpoint).
    Using `str(value)` instead of `float(value)` preserves precision:
    a price like Decimal("67000.123456789") round-trips exactly.

    Clients that need arithmetic can parseFloat() at the display
    layer; the raw string is the authoritative representation.
    """
    if value is None:
        return None
    try:
        return str(value)
    except Exception:
        return None


def _serialize_provider_price(pp) -> dict:
    """Serialize a ProviderPrice to a JSON-safe dict."""
    return {
        "provider":   pp.provider,
        "quote":      pp.quote,
        "price":      _serialize_decimal(pp.price),
        "change_24h": float(pp.change_24h) if pp.change_24h is not None else None,
        "volume_24h": _serialize_decimal(pp.volume_24h),
        "updated_at": (
            pp.updated_at.isoformat() if pp.updated_at else None
        ),
    }


def _serialize_coin(coin) -> dict:
    """
    Serialize a CoinData to a JSON-safe dict.

    Shape:
        {
            "canonical":  "BTC",
            "name":       "Bitcoin" | null,
            "symbol_display": "BTC",
            "icon_url":   "https://..." | null,
            "provider_prices": {
                "nobitex": [
                    {"provider": "nobitex", "quote": "USDT",
                     "price": "67000.5", "change_24h": 2.4,
                     "volume_24h": "1234.5", "updated_at": "..."},
                    {"provider": "nobitex", "quote": "RLS", ...}
                ],
                "coingecko": [
                    {"provider": "coingecko", "quote": "USD", ...}
                ]
            },
            "reference_prices": {
                "USDT": "67000.5",
                "RLS":  "6065292250",
                "USD":  "67000.5"
            },
            "price_dispersion_pct": {
                "USDT": 0.35,
                "USD":  null
            },
            "available_quotes": ["RLS", "USD", "USDT"],
            "sources": ["coingecko", "nobitex"],
            "updated_at": "2026-11-08T10:49:00Z" | null
        }
    """
    return {
        "canonical":      coin.canonical,
        "name":           coin.name,
        "symbol_display": coin.symbol_display,
        "icon_url":       coin.icon_url,
        "provider_prices": {
            provider: [
                _serialize_provider_price(pp)
                for pp in price_list
            ]
            for provider, price_list in coin.provider_prices.items()
        },
        "reference_prices": {
            quote: _serialize_decimal(price)
            for quote, price in coin.reference_prices.items()
        },
        "price_dispersion_pct": {
            quote: (float(pct) if pct is not None else None)
            for quote, pct in coin.price_dispersion_pct.items()
        },
        "available_quotes": list(coin.available_quotes),
        "sources":          list(coin.sources),
        "updated_at": (
            coin.updated_at.isoformat() if coin.updated_at else None
        ),
    }


# --------------------------------------------------------------
# Route registration
# --------------------------------------------------------------
def register_routes(
    http_api: Any,
    service: CryptoMarketService,
    db_service: Any,
    logger: Any,
) -> None:
    """
    Register all crypto_market routes on the given FastAPI app.
    """

    # ----------------------------------------------------------
    # POST /crypto/presence/heartbeat
    # ----------------------------------------------------------
    @http_api.post(
        "/crypto/presence/heartbeat",
        response_class=http_api.JSONResponse,
    )
    async def presence_heartbeat(request: http_api.Request):
        """
        Record a UI heartbeat. Body: {"kinds": [...]} (optional).

        Called by crypto_coins / crypto_charts partials every ~30s.
        Does NOT trigger a fetch — the poller's loop is the only
        consumer of presence state.
        """
        session_id, err = await _ensure_authenticated(
            request, db_service, logger
        )
        if err is not None:
            return http_api.JSONResponse(
                content=err["body"], status_code=err["status_code"]
            )

        body, err = await _parse_body(request)
        if err is not None:
            return http_api.JSONResponse(
                content=err["body"], status_code=err["status_code"]
            )

        kinds = _sanitize_kinds(body.get("kinds"))

        try:
            service.heartbeat(session_id, kinds)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Presence heartbeat failed: {exc}",
                    level="ERROR", tag="crypto_market",
                )
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": "internal_error",
                    "message": "Failed to record heartbeat.",
                },
                status_code=500,
            )

        return _json_success(http_api)

    # ----------------------------------------------------------
    # POST /crypto/presence/leave
    # ----------------------------------------------------------
    @http_api.post(
        "/crypto/presence/leave",
        response_class=http_api.JSONResponse,
    )
    async def presence_leave(request: http_api.Request):
        """
        Remove a session (or specific kinds) from presence.

        Body: {"kinds": [...]} (optional). Missing/empty kinds →
        remove the entire session.
        """
        session_id, err = await _ensure_authenticated(
            request, db_service, logger
        )
        if err is not None:
            return http_api.JSONResponse(
                content=err["body"], status_code=err["status_code"]
            )

        body, err = await _parse_body(request)
        if err is not None:
            return http_api.JSONResponse(
                content=err["body"], status_code=err["status_code"]
            )

        kinds = _sanitize_kinds(body.get("kinds"))

        try:
            service.leave(session_id, kinds)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Presence leave failed: {exc}",
                    level="ERROR", tag="crypto_market",
                )
            return http_api.JSONResponse(
                content={
                    "status": "error",
                    "code": "internal_error",
                    "message": "Failed to record leave.",
                },
                status_code=500,
            )

        return _json_success(http_api)

    # ----------------------------------------------------------
    # POST /crypto/market/api/coins
    # ----------------------------------------------------------
    @http_api.post(
        "/crypto/market/api/coins",
        response_class=http_api.JSONResponse,
    )
    async def market_coins(request: http_api.Request):
        """
        Return the current aggregated coin snapshot as JSON.

        Access: requires `crypto.coins.view` grant.

        Body (all optional):
            {
                "canonicals": ["BTC", "ETH"],  // filter by canonical
                "refresh":    true | "force"   // true → debounced,
                                               // "force" → immediate
            }

        Response:
            {
                "status":    "success",
                "coins":     [ <serialized CoinData>, ... ],
                "count":     <int>,
                "has_data":  <bool>,   // true if any poll cycle ran
            }

        Note on empty data:
            If the poller has not completed a cycle yet (e.g. no
            provider registered, or no UI active), `coins` is []. The
            caller may pass `refresh: "force"` to trigger a fresh
            cycle and retry. Consumers (crypto_coins UI) should
            display a "loading" state on empty + has_data=false, and
            an "empty" state on empty + has_data=true.

        Refresh semantics:
            • missing     → read snapshot (fast, no provider call)
            • true        → refresh_now(force=False) (3s debounce)
            • "force"     → refresh_now(force=True)  (bypass debounce)
        """
        # --- 1. Auth + grant -----------------------------------
        user_id, access_err = await _check_coins_access(
            request, db_service, logger
        )
        if access_err is not None:
            return http_api.JSONResponse(
                content=access_err["body"],
                status_code=access_err["status_code"],
            )

        # --- 2. Parse body -------------------------------------
        body, err = await _parse_body(request)
        if err is not None:
            return http_api.JSONResponse(
                content=err["body"], status_code=err["status_code"]
            )

        # --- 3. Optional refresh -------------------------------
        refresh = body.get("refresh")
        if refresh is True:
            try:
                await service.refresh_now(force=False)
            except Exception as exc:
                if logger:
                    logger.log(
                        f"refresh_now(force=False) failed: {exc}",
                        level="WARNING", tag="crypto_market",
                    )
        elif isinstance(refresh, str) and refresh.strip().lower() == "force":
            try:
                await service.refresh_now(force=True)
            except Exception as exc:
                if logger:
                    logger.log(
                        f"refresh_now(force=True) failed: {exc}",
                        level="WARNING", tag="crypto_market",
                    )

        # --- 4. Sanitize canonicals ----------------------------
        raw_canonicals = body.get("canonicals")
        canonicals: Optional[list[str]] = None
        if isinstance(raw_canonicals, list):
            cleaned = []
            seen = set()
            for c in raw_canonicals:
                if not isinstance(c, str):
                    continue
                c = c.strip().upper()
                if not c or c in seen:
                    continue
                seen.add(c)
                cleaned.append(c)
                if len(cleaned) >= 500:
                    break
            canonicals = cleaned or None

        # --- 5. Read snapshot ----------------------------------
        try:
            coins = await service.get_coins(canonicals=canonicals)
        except Exception as exc:
            if logger:
                logger.log(
                    f"get_coins failed: {exc}",
                    level="ERROR", tag="crypto_market",
                )
            return http_api.JSONResponse(
                content={
                    "status":  "error",
                    "code":    "internal_error",
                    "message": "Failed to read coin snapshot.",
                },
                status_code=500,
            )

        # --- 6. Serialize and return ---------------------------
        serialized = [_serialize_coin(c) for c in coins]

        return http_api.JSONResponse(
            content={
                "status":   "success",
                "coins":    serialized,
                "count":    len(serialized),
                "has_data": service.has_data(),
            },
            status_code=200,
        )


__all__ = ["register_routes"]
