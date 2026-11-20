"""
routes — JSON and HTML endpoints for crypto_coins.

Endpoints
---------
    POST /crypto/coins/api/list
        JSON. Returns column descriptors + row data for <ramz-table>.
        Reads the current poller snapshot (refreshing it if empty,
        debounced to avoid hammering providers).

    POST /crypto/coins/partials/list
        HTML. Renders the coins list partial (a <ramz-card> wrapping
        a <ramz-table> pointed at the JSON endpoint). Consumed by
        user_panel's content-container when the sidebar item is
        clicked (extension registered in TASK 79.7).

Auth
----
Both endpoints require:
    • Valid session (session cookie + enabled + not revoked).
    • `crypto.coins.view` grant.

Mutations (favorites, display currency) arrive in TASK 79.4/79.5.

Design
------
Serialization is done here (not in CoinsService) because it is
presentation logic: the JSON shape expected by <ramz-table> would
couple CoinsService to a specific UI contract. CoinsService stays
UI-agnostic and returns raw CoinData objects.

Columns are:
    Coin       — avatar (initials) + name + canonical
    Nobitex    — Nobitex price (USDT preferred, else RLS)
    CoinGecko  — CoinGecko price (USD)
    Spread %   — price_dispersion_pct on the preferred quote
    Reference  — median price in the user's preferred currency

Sorting is by Nobitex USDT price (descending), falling back to
CoinGecko USD, then RLS, then canonical. This approximates "market
cap order" for the two-provider dataset without requiring a market-
cap field.

Currency preference is read from UserPreferenceRepository; default
"USDT". TASK 79.4 will add a settings UI to change it.
"""
from typing import Any, Optional
from html import escape as _html_escape

from app.crypto_market.market_data.types import CoinData


# ------------------------------------------------------------------
# Auth helpers (mirror crypto_providers/routes.py — no cross-module
# import of private helpers, copy is the authorized pattern)
# ------------------------------------------------------------------
async def _ensure_authenticated(request, db_service, logger):
    """
    Session + enabled + revoked checks.

    Returns (session_id, user_id) on success, (None, None) on failure.
    Fail-open on transient DB errors.
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
                    level="WARNING", tag="crypto_coins",
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
                    level="WARNING", tag="crypto_coins",
                )
            return None, None
    except Exception as exc:
        if logger:
            logger.log(
                f"Session check failed ({exc}); allowing request",
                level="WARNING", tag="crypto_coins",
            )

    return session_id, int(user_id)


async def _check_coins_view(request, db_service, logger):
    """
    Full access check for crypto.coins.view.

    Returns (user_id, None) on success, (None, error_dict) on failure.
    Fail-closed on grant-check errors.
    """
    session_id, user_id = await _ensure_authenticated(
        request, db_service, logger
    )
    if session_id is None or user_id is None:
        return None, {
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
                level="ERROR", tag="crypto_coins",
            )
        return None, {
            "status_code": 503,
            "body": {
                "status": "error",
                "code": "service_unavailable",
                "message": "Access control unavailable; try later.",
            },
        }

    try:
        allowed = await db_service.has_access(
            user_id, "crypto.coins.view"
        )
    except Exception as exc:
        if logger:
            logger.log(
                f"Grant check raised ({exc}); denying access "
                f"(fail-closed)",
                level="ERROR", tag="crypto_coins",
            )
        return None, {
            "status_code": 503,
            "body": {
                "status": "error",
                "code": "service_unavailable",
                "message": "Access control unavailable; try later.",
            },
        }

    if not allowed:
        return None, {
            "status_code": 403,
            "body": {
                "status": "error",
                "code": "no_permission",
                "message": "You do not have access to the coins list.",
            },
        }

    return user_id, None


async def _check_settings_access(request, db_service, logger):
    """
    Access check for crypto.coins.favorite (settings page).

    Parallel to _check_coins_view but with the favorite grant
    (higher privilege — favorites are user-curated, unlike the
    read-only coin list). Fail-closed on grant-check errors.
    """
    session_id, user_id = await _ensure_authenticated(
        request, db_service, logger
    )
    if session_id is None or user_id is None:
        return None, {
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
                level="ERROR", tag="crypto_coins",
            )
        return None, {
            "status_code": 503,
            "body": {
                "status": "error",
                "code": "service_unavailable",
                "message": "Access control unavailable; try later.",
            },
        }

    try:
        allowed = await db_service.has_access(
            user_id, "crypto.coins.favorite"
        )
    except Exception as exc:
        if logger:
            logger.log(
                f"Grant check raised ({exc}); denying access "
                f"(fail-closed)",
                level="ERROR", tag="crypto_coins",
            )
        return None, {
            "status_code": 503,
            "body": {
                "status": "error",
                "code": "service_unavailable",
                "message": "Access control unavailable; try later.",
            },
        }

    if not allowed:
        return None, {
            "status_code": 403,
            "body": {
                "status": "error",
                "code": "no_permission",
                "message": (
                    "You do not have permission to manage coin "
                    "settings."
                ),
            },
        }

    return user_id, None


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


# ------------------------------------------------------------------
# Serialization
# ------------------------------------------------------------------
def _format_price(value, currency: str) -> str:
    """
    Format a Decimal price for table display.

    Uses a compact notation for readability (no currency symbol in
    the string — the currency is in the column header). Very small
    values (<0.01) get more decimals.
    """
    if value is None:
        return "—"
    try:
        d = float(value)
    except (TypeError, ValueError):
        return "—"
    if d == 0:
        return "0"
    if abs(d) < 0.01:
        return f"{d:.6f}"
    if abs(d) < 1:
        return f"{d:.4f}"
    if abs(d) < 1000:
        return f"{d:,.2f}"
    return f"{d:,.0f}"


def _format_pct(value) -> str:
    """Format a percentage with a color hint. Returns escaped HTML."""
    if value is None:
        return '<span style="color:#94a3b8">—</span>'
    try:
        v = float(value)
    except (TypeError, ValueError):
        return '<span style="color:#94a3b8">—</span>'
    if v == 0:
        return '<span style="color:#94a3b8">0.00%</span>'
    color = "#34d399" if v > 0 else "#fb7185"
    return (
        f'<span style="color:{color}">{v:.2f}%</span>'
    )


def _pick_provider_quote_price(
    coin: CoinData,
    provider: str,
    preferred_quotes: tuple,
) -> tuple:
    """
    From coin.provider_prices[provider], return (price, quote) of the
    first entry whose quote is in `preferred_quotes`, or (None, None).
    """
    prices = coin.provider_prices.get(provider) or []
    if not prices:
        return None, None
    for pq in preferred_quotes:
        for pp in prices:
            if pp.quote == pq:
                return pp.price, pq
    # Fallback: first price regardless of quote
    return prices[0].price, prices[0].quote


def _serialize_coin_row(
    coin: CoinData, currency: str, favorites_set=None
) -> dict:
    """
    Build one <ramz-table> row for a CoinData.

    `favorites_set`: optional set of uppercase canonicals. When
    provided, the `_favorite` column shows a filled star for coins
    in the set. When None, all stars render as unfilled (safe
    default for callers without favorites context).

    See module docstring for column semantics.
    """
    canonical = coin.canonical or ""
    name = coin.name or canonical

    favorited = bool(
        favorites_set is not None
        and canonical
        and canonical.upper() in favorites_set
    )
    fav_icon  = "★" if favorited else "☆"
    fav_cls   = (
        "favorite-btn favorite-btn--active" if favorited
        else "favorite-btn"
    )
    fav_attr  = "1" if favorited else "0"
    fav_title = (
        "Remove from favorites" if favorited
        else "Add to favorites"
    )
    fav_color = "#fbbf24" if favorited else "#64748b"
    fav_html = (
        f'<button type="button" class="{fav_cls}" '
        f'data-canonical="{_html_escape(canonical)}" '
        f'data-favorited="{fav_attr}" '
        f'title="{fav_title}" '
        f'aria-label="{fav_title}" '
        f'style="background:transparent;border:none;'
        f'cursor:pointer;font-size:18px;line-height:1;'
        f'padding:4px 6px;color:{fav_color};'
        f'transition:color 120ms;">{fav_icon}</button>'
    )

    # Preferred quote for sort/display: user's currency
    preferred = (currency or "USDT", "USDT", "USD", "RLS")

    # Reference price (median in user's currency)
    reference_price = coin.reference_prices.get(currency)
    if reference_price is None:
        # Try alternates if user's currency isn't available
        for alt in ("USDT", "USD", "RLS"):
            reference_price = coin.reference_prices.get(alt)
            if reference_price is not None:
                break

    # Dispersion on the preferred quote
    spread = coin.price_dispersion_pct.get(currency)
    if spread is None:
        for alt in ("USDT", "USD", "RLS"):
            if alt in coin.price_dispersion_pct:
                spread = coin.price_dispersion_pct[alt]
                break

    # Nobitex price (USDT preferred, else RLS)
    nobitex_price, _ = _pick_provider_quote_price(
        coin, "nobitex", ("USDT", "RLS")
    )

    # CoinGecko price (USD preferred)
    coingecko_price, _ = _pick_provider_quote_price(
        coin, "coingecko", ("USD",)
    )

    # Sources count as a badge
    sources = coin.sources or []
    sources_count = len(sources)
    if sources_count >= 2:
        sources_badge = {
            "text": str(sources_count),
            "variant": "active",
        }
    elif sources_count == 1:
        sources_badge = {
            "text": str(sources_count),
            "variant": "idle",
        }
    else:
        sources_badge = {"text": "—", "variant": "idle"}

    initials = canonical[:2].upper() if canonical else "?"

    return {
        "_favorite":   fav_html,
        "_coin": {
            "initials":    initials,
            "name":        name,
            "email":       canonical,
            "avatarClass": "avatar--indigo",
        },
        "_nobitex":    _format_price(nobitex_price, "USDT"),
        "_coingecko":  _format_price(coingecko_price, "USD"),
        "_spread":     _format_pct(spread),
        "_sources":    sources_badge,
        "_reference":  _format_price(reference_price, currency),
    }


def _sort_key(coin: CoinData):
    """
    Sort key: nobitex USDT price desc, then coingecko USD desc,
    then RLS desc, then canonical asc.
    """
    nb, _ = _pick_provider_quote_price(coin, "nobitex", ("USDT",))
    if nb is None:
        nb, _ = _pick_provider_quote_price(coin, "nobitex", ("RLS",))
    cg, _ = _pick_provider_quote_price(coin, "coingecko", ("USD",))

    def _num(x):
        try:
            return -float(x) if x is not None else float("inf")
        except (TypeError, ValueError):
            return float("inf")

    return (
        _num(nb),
        _num(cg),
        (coin.canonical or ""),
    )


# ------------------------------------------------------------------
# Route registration
# ------------------------------------------------------------------
def register_routes(
    http_api: Any,
    coins_service: Any,
    preference_repo: Any,
    db_service: Any,
    template_service: Any,
    logger: Any,
) -> None:
    """Register all crypto_coins routes."""

    # ----------------------------------------------------------
    # POST /crypto/coins/api/list
    # ----------------------------------------------------------
    @http_api.post(
        "/crypto/coins/api/list",
        response_class=http_api.JSONResponse,
    )
    async def coins_api_list(request: http_api.Request):
        """
        Return the coin list as JSON for <ramz-table>.

        Response:
            {
                "status":   "success",
                "currency": "USDT",
                "total":    281,
                "has_data": true,
                "columns":  [...],
                "rows":     [...]
            }

        If no poll cycle has completed yet, triggers a debounced
        refresh and returns whatever is available.
        """
        user_id, err = await _check_coins_view(
            request, db_service, logger
        )
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        if coins_service is None:
            return _json_error(
                http_api, 503, "service_unavailable",
                "Coins service unavailable.",
            )

        # Refresh (debounced in CoinsService → refresh_now(force=False))
        # Only if no data yet — otherwise rely on the poller snapshot.
        try:
            if not coins_service.has_data():
                await coins_service.refresh_now(force=False)
        except Exception as exc:
            if logger:
                logger.log(
                    f"refresh_now in list endpoint failed: {exc}",
                    level="WARNING", tag="crypto_coins",
                )

        # Read preferences
        currency = "USDT"
        favorites_list = []
        if preference_repo is not None:
            try:
                currency = await preference_repo.get_display_currency(
                    user_id
                )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"get_display_currency failed ({exc}); "
                        f"using USDT",
                        level="WARNING", tag="crypto_coins",
                    )
            try:
                favorites_list = await preference_repo.get_favorites(
                    user_id
                )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"get_favorites failed ({exc}); using []",
                        level="WARNING", tag="crypto_coins",
                    )
        favorites_set = set(favorites_list or [])

        # Fetch data
        try:
            coins = await coins_service.get_coins()
        except Exception as exc:
            if logger:
                logger.log(
                    f"get_coins failed: {exc}",
                    level="ERROR", tag="crypto_coins",
                )
            return _json_error(
                http_api, 500, "internal_error",
                "Failed to load coins.",
            )

        # Sort by price descending (approximates market cap)
        try:
            coins_sorted = sorted(coins, key=_sort_key)
        except Exception:
            coins_sorted = coins

        # Serialize
        rows = [
            _serialize_coin_row(c, currency, favorites_set)
            for c in coins_sorted
        ]

        # Fallback: if the snapshot is empty but has_data is true,
        # the previous poll cycle produced no CoinData (all providers
        # failed transiently, or all rows were currencies). Trigger a
        # forced refresh once and retry. This makes the first render
        # after a server restart / transient outage self-healing
        # without requiring the user to click Refresh twice.
        if not rows:
            if logger:
                logger.log(
                    "coins_api_list: snapshot empty; attempting "
                    "force refresh",
                    level="INFO", tag="crypto_coins",
                )
            try:
                await coins_service.refresh_now(force=True)
            except Exception as exc:
                if logger:
                    logger.log(
                        f"force refresh failed: {exc}",
                        level="WARNING", tag="crypto_coins",
                    )
            try:
                coins = await coins_service.get_coins()
                coins_sorted = sorted(coins, key=_sort_key)
                rows = [
                    _serialize_coin_row(c, currency, favorites_set)
                    for c in coins_sorted
                ]
                if not rows and logger:
                    logger.log(
                        "coins_api_list: still empty after force "
                        "refresh; providers may be temporarily "
                        "unavailable",
                        level="WARNING", tag="crypto_coins",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"re-fetch after force refresh failed: {exc}",
                        level="ERROR", tag="crypto_coins",
                    )

        columns = [
            {"key": "_favorite",  "label": "",
             "type": "html",      "align": "center",
             "className": "favorite-cell"},
            {"key": "_coin",      "label": "Coin",
             "type": "avatar"},
            {"key": "_nobitex",   "label": "Nobitex",
             "type": "text",      "align": "right",
             "className": "amount"},
            {"key": "_coingecko", "label": "CoinGecko",
             "type": "text",      "align": "right",
             "className": "amount"},
            {"key": "_spread",    "label": "Spread %",
             "type": "html",      "align": "right",
             "className": "amount"},
            {"key": "_reference", "label": f"Reference ({currency})",
             "type": "text",      "align": "right",
             "className": "amount"},
        ]

        return http_api.JSONResponse(
            content={
                "status":   "success",
                "currency": currency,
                "total":    len(rows),
                "has_data": coins_service.has_data(),
                "columns":  columns,
                "rows":     rows,
            },
            status_code=200,
        )

    # ----------------------------------------------------------
    # POST /crypto/coins/partials/list
    # ----------------------------------------------------------
    @http_api.post(
        "/crypto/coins/partials/list",
        response_class=http_api.HTMLResponse,
    )
    async def coins_partial_list(request: http_api.Request):
        """
        Render the coins list HTML shell.

        The shell contains a <ramz-table> whose `endpoint` points to
        the JSON endpoint above. On connectedCallback, <ramz-table>
        auto-fetches and renders itself. No custom JS here.
        """
        user_id, err = await _check_coins_view(
            request, db_service, logger
        )
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        if template_service is None:
            return http_api.HTMLResponse(
                content=(
                    "<div class='card'><p>"
                    "Template service unavailable."
                    "</p></div>"
                ),
                status_code=500,
            )

        context = {
            "module_name":  "crypto_coins",
            "current_user": request.session.get("user") or {},
        }

        try:
            html = await template_service.render(
                "partials/coins_list.html", context
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"coins_list render failed: {exc}",
                    level="ERROR", tag="crypto_coins",
                )
            return http_api.HTMLResponse(
                content=(
                    "<div class='card'><p>"
                    "Failed to render coins list."
                    "</p></div>"
                ),
                status_code=500,
            )
        return http_api.HTMLResponse(content=html)

    # ----------------------------------------------------------
    # POST /crypto/coins/api/favorite/toggle
    # ----------------------------------------------------------
    @http_api.post(
        "/crypto/coins/api/favorite/toggle",
        response_class=http_api.JSONResponse,
    )
    async def coins_api_favorite_toggle(request: http_api.Request):
        """
        Toggle a coin in/out of the current user's favorites.

        Reuses `_check_settings_access` because the same grant
        (`crypto.coins.favorite`) covers both favorites and display
        settings (per schema v11: "manage favorites + settings").

        Body (JSON or form-encoded — Content-Type aware):
            {
                "canonical": "BTC",
                "action":    "add" | "remove"
            }

        Both fields are required. `canonical` is uppercased and
        deduped by the repository. `action` is explicitly required
        (not inferred) so the operation is idempotent and the client
        knows the intended transition.

        Response:
            {
                "status":    "success",
                "canonical": "BTC",
                "favorited": true,
                "favorites": ["BTC", "ETH"]
            }
        """
        user_id, err = await _check_settings_access(
            request, db_service, logger
        )
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        if preference_repo is None:
            return _json_error(
                http_api, 503, "service_unavailable",
                "Preferences unavailable.",
            )

        # Content-Type aware body parsing (matches settings/save).
        content_type = (
            request.headers.get("content-type") or ""
        ).lower()
        body: dict = {}
        try:
            if "application/json" in content_type:
                parsed = await request.json()
                if isinstance(parsed, dict):
                    body = parsed
            elif (
                "multipart/form-data" in content_type
                or "application/x-www-form-urlencoded" in content_type
            ):
                form = await request.form()
                body = dict(form)
        except Exception as exc:
            if logger:
                logger.log(
                    f"favorite toggle body parse failed: {exc}",
                    level="WARNING", tag="crypto_coins",
                )
            return _json_error(
                http_api, 400, "invalid_body",
                "Malformed request body.",
            )

        canonical_raw = body.get("canonical")
        if not canonical_raw or not str(canonical_raw).strip():
            return _json_error(
                http_api, 400, "missing_canonical",
                "Field 'canonical' is required.",
            )

        action_raw = body.get("action")
        if action_raw is None or not str(action_raw).strip():
            return _json_error(
                http_api, 400, "missing_action",
                "Field 'action' is required (add or remove).",
            )

        action = str(action_raw).strip().lower()
        if action not in ("add", "remove"):
            return _json_error(
                http_api, 400, "invalid_action",
                "Field 'action' must be 'add' or 'remove'.",
            )

        canonical = str(canonical_raw).strip().upper()

        if action == "add":
            ok, favorites = await preference_repo.add_favorite(
                user_id, canonical
            )
        else:
            ok, favorites = await preference_repo.remove_favorite(
                user_id, canonical
            )

        if not ok:
            if logger:
                logger.log(
                    f"favorite {action} failed for user_id={user_id}, "
                    f"canonical={canonical}",
                    level="ERROR", tag="crypto_coins",
                )
            return _json_error(
                http_api, 500, "internal_error",
                "Failed to update favorites.",
            )

        favorited = canonical in (favorites or [])

        if logger:
            logger.log(
                f"favorite {action} for user_id={user_id}: "
                f"{canonical} (now favorited={favorited})",
                tag="crypto_coins",
            )

        return http_api.JSONResponse(
            content={
                "status":    "success",
                "canonical": canonical,
                "favorited": favorited,
                "favorites": favorites,
            },
            status_code=200,
        )

    # ----------------------------------------------------------
    # POST /crypto/coins/api/settings
    # ----------------------------------------------------------
    @http_api.post(
        "/crypto/coins/api/settings",
        response_class=http_api.JSONResponse,
    )
    async def coins_api_settings(request: http_api.Request):
        """
        Return the current user's coin settings as JSON.

        Requires `crypto.coins.favorite` grant (settings are higher
        privilege than read-only coin list viewing).

        Response:
            {
                "status":           "success",
                "display_currency": "USDT",
                "rows_per_page":    50,
                "favorites":        ["BTC", "ETH"],
                "available_currencies": ["USDT", "RLS", "USD"],
                "min_rows": 10,
                "max_rows": 500
            }
        """
        user_id, err = await _check_settings_access(
            request, db_service, logger
        )
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        if preference_repo is None:
            return _json_error(
                http_api, 503, "service_unavailable",
                "Preferences unavailable.",
            )

        try:
            currency = await preference_repo.get_display_currency(
                user_id
            )
            rows = await preference_repo.get_rows_per_page(user_id)
            favorites = await preference_repo.get_favorites(user_id)
        except Exception as exc:
            if logger:
                logger.log(
                    f"settings read failed: {exc}",
                    level="ERROR", tag="crypto_coins",
                )
            return _json_error(
                http_api, 500, "internal_error",
                "Failed to read preferences.",
            )

        # Local import to avoid a top-level import that could leak
        # through __init__ ordering; constants are stable.
        from .repositories import (
            VALID_DISPLAY_CURRENCIES,
            MIN_ROWS_PER_PAGE,
            MAX_ROWS_PER_PAGE,
        )

        return http_api.JSONResponse(
            content={
                "status":               "success",
                "display_currency":     currency,
                "rows_per_page":        rows,
                "favorites":            favorites,
                "available_currencies": sorted(VALID_DISPLAY_CURRENCIES),
                "min_rows":             MIN_ROWS_PER_PAGE,
                "max_rows":             MAX_ROWS_PER_PAGE,
            },
            status_code=200,
        )

    # ----------------------------------------------------------
    # POST /crypto/coins/api/settings/save
    # ----------------------------------------------------------
    @http_api.post(
        "/crypto/coins/api/settings/save",
        response_class=http_api.JSONResponse,
    )
    async def coins_api_settings_save(request: http_api.Request):
        """
        Save display currency and rows-per-page.

        No password prompt: these are display preferences, not
        security-sensitive operations. (Favorites are managed via
        TASK 79.5 endpoints.)

        Body (JSON or form-encoded — Content-Type aware):
            {
                "display_currency": "USDT" | "RLS" | "USD",
                "rows_per_page":    10..500
            }

        Either field may be omitted — the corresponding preference is
        left unchanged.

        Response:
            {"status": "success", "message": "Settings saved."}
        """
        user_id, err = await _check_settings_access(
            request, db_service, logger
        )
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        if preference_repo is None:
            return _json_error(
                http_api, 503, "service_unavailable",
                "Preferences unavailable.",
            )

        # Content-Type aware body parsing (multipart form OR JSON).
        # Mirrors crypto_providers/routes.py::_parse_body, but local
        # to crypto_coins to keep modules independent.
        content_type = (
            request.headers.get("content-type") or ""
        ).lower()
        body: dict = {}
        try:
            if "application/json" in content_type:
                parsed = await request.json()
                if isinstance(parsed, dict):
                    body = parsed
            elif (
                "multipart/form-data" in content_type
                or "application/x-www-form-urlencoded" in content_type
            ):
                form = await request.form()
                body = dict(form)
        except Exception as exc:
            if logger:
                logger.log(
                    f"body parse failed: {exc}",
                    level="WARNING", tag="crypto_coins",
                )
            return _json_error(
                http_api, 400, "invalid_body",
                "Malformed request body.",
            )

        # Validate + apply. Use flags to report which parts were
        # actually updated (useful for the client if it wants to
        # show a partial-success message).
        saved: list[str] = []

        currency_raw = body.get("display_currency")
        if currency_raw is not None and str(currency_raw).strip():
            try:
                ok = await preference_repo.set_display_currency(
                    user_id, str(currency_raw)
                )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"set_display_currency failed: {exc}",
                        level="ERROR", tag="crypto_coins",
                    )
                ok = False
            if not ok:
                return _json_error(
                    http_api, 400, "invalid_currency",
                    "Display currency must be one of "
                    "USDT, RLS, USD.",
                )
            saved.append("display_currency")

        rows_raw = body.get("rows_per_page")
        if rows_raw is not None and str(rows_raw).strip():
            try:
                ok = await preference_repo.set_rows_per_page(
                    user_id, int(rows_raw)
                )
            except (TypeError, ValueError):
                ok = False
            except Exception as exc:
                if logger:
                    logger.log(
                        f"set_rows_per_page failed: {exc}",
                        level="ERROR", tag="crypto_coins",
                    )
                ok = False
            if not ok:
                return _json_error(
                    http_api, 400, "invalid_rows_per_page",
                    "Rows per page must be an integer between 10 "
                    "and 500.",
                )
            saved.append("rows_per_page")

        if not saved:
            return _json_error(
                http_api, 400, "empty_fields",
                "No valid fields to save.",
            )

        if logger:
            logger.log(
                f"coin settings saved for user_id={user_id}: "
                f"{saved}",
                tag="crypto_coins",
            )

        return http_api.JSONResponse(
            content={
                "status":  "success",
                "message": "Settings saved.",
                "saved":   saved,
            },
            status_code=200,
        )

    # ----------------------------------------------------------
    # POST /crypto/coins/partials/settings
    # ----------------------------------------------------------
    @http_api.post(
        "/crypto/coins/partials/settings",
        response_class=http_api.HTMLResponse,
    )
    async def coins_partial_settings(request: http_api.Request):
        """
        Render the coin settings partial (HTML shell).

        The shell reads current preferences via the API endpoint
        after mount (inline JS below), then handles save via fetch.
        """
        user_id, err = await _check_settings_access(
            request, db_service, logger
        )
        if err is not None:
            return _json_error(
                http_api, err["status_code"],
                err["body"]["code"], err["body"]["message"],
            )

        if template_service is None:
            return http_api.HTMLResponse(
                content=(
                    "<div class='card'><p>"
                    "Template service unavailable."
                    "</p></div>"
                ),
                status_code=500,
            )

        context = {
            "module_name":  "crypto_coins",
            "current_user": request.session.get("user") or {},
        }

        try:
            html = await template_service.render(
                "partials/coins_settings.html", context
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"coins_settings render failed: {exc}",
                    level="ERROR", tag="crypto_coins",
                )
            return http_api.HTMLResponse(
                content=(
                    "<div class='card'><p>"
                    "Failed to render coin settings."
                    "</p></div>"
                ),
                status_code=500,
            )
        return http_api.HTMLResponse(content=html)


__all__ = ["register_routes"]
