"""
user_preference_repository — CRUD on `crypto_user_preference`.

Table schema (migration v10→v11):
    crypto_user_preference(
        user_id INTEGER NOT NULL,   → FK user(user_id), CASCADE
        module  TEXT NOT NULL,      -- namespace (e.g., "coins")
        key     TEXT NOT NULL,      -- e.g., "favorites", "display_currency"
        value   TEXT,               -- free-form; JSON for complex types
        PRIMARY KEY (user_id, module, key)
    )

Namespace scoping
-----------------
The `module` column lets multiple modules share this table without
collision. The repository is constructed with `module_name` (e.g.,
"coins") and every read/write is transparently scoped to it. So
crypto_coins and crypto_charts can each store their own "favorites"
(or any other key) without seeing each other's data.

Value encoding
--------------
The DB column is TEXT. For simple string prefs (e.g., display_currency)
the string is stored as-is. For structured prefs (e.g., a list of
favorite canonicals) the repository helper JSON-encodes and decodes.
Raw `get(key)` / `set(key, value)` operate on plain strings — helper
methods (`get_favorites`, `set_favorites`, ...) are what most callers
should use.

Defaults
--------
Every "get" helper has a sensible default so callers never need to
handle "no preference stored" as a special case:

    favorites         → []
    display_currency  → "USDT"
    rows_per_page     → 50

BLOB normalization is not needed here (values are strings). No cache:
the table is tiny per-user (≤5 rows typically), and the settings/
list routes read it at most once per request.

DB portability
--------------
All queries use the framework's high-level `find_one`/`find_many`/
`insert`/`update`/`delete` methods (dict-based, no SQL string
literals), matching the pattern of `symbol_map_repository` and
`credential_repository`.
"""
import json
from typing import Optional


# ------------------------------------------------------------------
# Known preference keys (per module)
# ------------------------------------------------------------------
KEY_FAVORITES         = "favorites"
KEY_DISPLAY_CURRENCY  = "display_currency"
KEY_ROWS_PER_PAGE     = "rows_per_page"

# ------------------------------------------------------------------
# Defaults
# ------------------------------------------------------------------
DEFAULT_DISPLAY_CURRENCY = "USDT"
DEFAULT_ROWS_PER_PAGE    = 50
VALID_DISPLAY_CURRENCIES = frozenset({"USDT", "RLS", "USD"})
MIN_ROWS_PER_PAGE        = 10
MAX_ROWS_PER_PAGE        = 500


class UserPreferenceRepository:
    """
    Per-user, per-module preference CRUD.

    See module docstring for scoping, encoding, and defaults.
    """

    TABLE = "crypto_user_preference"

    def __init__(self, db_service, module_name: str, logger=None):
        if not module_name:
            raise ValueError("module_name is required")
        self._db = db_service
        self._module = module_name
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    def _log(self, message, level="INFO"):
        if self._logger:
            try:
                self._logger.log(
                    message, level=level, tag="crypto_coins"
                )
            except Exception:
                pass

    # ==========================================================
    # Raw key/value CRUD
    # ==========================================================
    async def get(self, user_id: int, key: str) -> Optional[str]:
        """
        Return the stored raw string for `key`, or None.

        Callers that need a typed value should use the helper
        methods (`get_favorites`, `get_display_currency`, ...).
        """
        if not user_id or not key:
            return None
        try:
            row = await self._conn().find_one(
                self.TABLE,
                where={
                    "user_id": int(user_id),
                    "module":  self._module,
                    "key":     key,
                },
            )
            return row.get("value") if row else None
        except Exception as exc:
            self._log(f"get({key}) failed: {exc}", level="ERROR")
            return None

    async def set(
        self, user_id: int, key: str, value: str
    ) -> bool:
        """
        Upsert the raw string value for `key`.

        `value` is stored as TEXT verbatim. For JSON structures, the
        helper methods (`set_favorites`) handle encoding — callers
        using `set` directly are responsible for whatever encoding
        they want.

        An empty string is stored as-is (distinct from "no row").
        Use `delete()` to remove a row entirely.
        """
        if not user_id or not key:
            return False
        if value is None:
            return False

        where = {
            "user_id": int(user_id),
            "module":  self._module,
            "key":     key,
        }
        try:
            existing = await self._conn().find_one(
                self.TABLE, where=where
            )
            if existing:
                result = await self._conn().update(
                    self.TABLE,
                    data={"value": value},
                    where=where,
                )
            else:
                result = await self._conn().insert(
                    self.TABLE,
                    data={
                        "user_id": int(user_id),
                        "module":  self._module,
                        "key":     key,
                        "value":   value,
                    },
                )
            return bool(getattr(result, "success", False))
        except Exception as exc:
            self._log(f"set({key}) failed: {exc}", level="ERROR")
            return False

    async def delete(self, user_id: int, key: str) -> bool:
        """Delete one preference row. Idempotent."""
        if not user_id or not key:
            return False
        try:
            result = await self._conn().delete(
                self.TABLE,
                where={
                    "user_id": int(user_id),
                    "module":  self._module,
                    "key":     key,
                },
            )
            return bool(getattr(result, "success", False))
        except Exception as exc:
            self._log(f"delete({key}) failed: {exc}", level="ERROR")
            return False

    async def delete_all(self, user_id: int) -> bool:
        """Delete every preference for the module. Idempotent."""
        if not user_id:
            return False
        try:
            result = await self._conn().delete(
                self.TABLE,
                where={
                    "user_id": int(user_id),
                    "module":  self._module,
                },
            )
            return bool(getattr(result, "success", False))
        except Exception as exc:
            self._log(f"delete_all failed: {exc}", level="ERROR")
            return False

    async def get_all(self, user_id: int) -> dict[str, str]:
        """
        Return every stored (key, value) pair for the module.

        Missing rows are not included. If no rows exist, returns {}.
        """
        if not user_id:
            return {}
        try:
            rows = await self._conn().find_many(
                self.TABLE,
                where={
                    "user_id": int(user_id),
                    "module":  self._module,
                },
            )
            result: dict[str, str] = {}
            for row in rows or []:
                k = row.get("key")
                v = row.get("value")
                if isinstance(k, str) and v is not None:
                    result[k] = v
            return result
        except Exception as exc:
            self._log(f"get_all failed: {exc}", level="ERROR")
            return {}

    # ==========================================================
    # Favorites helpers
    # ==========================================================
    async def get_favorites(self, user_id: int) -> list[str]:
        """
        Return the user's favorite canonical symbols (uppercase).

        Never raises. Returns [] if unset or malformed. Preserves
        stored order (insertion order is meaningful to the user —
        new favorites appended at the end).
        """
        raw = await self.get(user_id, KEY_FAVORITES)
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            self._log(
                "favorites value is not valid JSON; returning []",
                level="WARNING",
            )
            return []
        if not isinstance(data, list):
            return []
        # Sanitize: strings only, uppercase, no duplicates, order kept
        seen = set()
        result: list[str] = []
        for item in data:
            if not isinstance(item, str):
                continue
            sym = item.strip().upper()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            result.append(sym)
        return result

    async def set_favorites(
        self, user_id: int, symbols: list[str]
    ) -> bool:
        """
        Overwrite the favorites list.

        `symbols` is sanitized (strings only, uppercase, deduped,
        order preserved). Empty list is stored as "[]" — distinct
        from "no row" (which `get_favorites` also treats as []).
        """
        if not isinstance(symbols, list):
            return False
        cleaned: list[str] = []
        seen = set()
        for item in symbols:
            if not isinstance(item, str):
                continue
            sym = item.strip().upper()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            cleaned.append(sym)
        try:
            raw = json.dumps(cleaned, separators=(",", ":"))
        except Exception:
            return False
        return await self.set(user_id, KEY_FAVORITES, raw)

    async def add_favorite(
        self, user_id: int, canonical: str
    ) -> tuple[bool, list[str]]:
        """
        Append a canonical to favorites if not already present.

        Returns (ok, updated_list). `ok` is True on success,
        including the no-op case (already present). On error,
        returns (False, current_list_unchanged).

        Idempotent: adding an existing favorite is a success.
        """
        if not canonical:
            return False, []
        sym = canonical.strip().upper()
        if not sym:
            return False, []

        current = await self.get_favorites(user_id)
        if sym in current:
            return True, current
        current.append(sym)
        ok = await self.set_favorites(user_id, current)
        return ok, current if ok else await self.get_favorites(user_id)

    async def remove_favorite(
        self, user_id: int, canonical: str
    ) -> tuple[bool, list[str]]:
        """
        Remove a canonical from favorites if present.

        Returns (ok, updated_list). Idempotent: removing a
        non-present favorite is a success (no change).
        """
        if not canonical:
            return False, []
        sym = canonical.strip().upper()
        if not sym:
            return False, []

        current = await self.get_favorites(user_id)
        if sym not in current:
            return True, current
        current = [s for s in current if s != sym]
        ok = await self.set_favorites(user_id, current)
        return ok, current if ok else await self.get_favorites(user_id)

    # ==========================================================
    # Display currency helpers
    # ==========================================================
    async def get_display_currency(self, user_id: int) -> str:
        """
        Return the user's preferred display currency.

        Returns DEFAULT_DISPLAY_CURRENCY ("USDT") if unset or
        invalid. Never raises.
        """
        raw = await self.get(user_id, KEY_DISPLAY_CURRENCY)
        if not raw:
            return DEFAULT_DISPLAY_CURRENCY
        cur = raw.strip().upper()
        if cur not in VALID_DISPLAY_CURRENCIES:
            return DEFAULT_DISPLAY_CURRENCY
        return cur

    async def set_display_currency(
        self, user_id: int, currency: str
    ) -> bool:
        """
        Set the display currency. Rejects values not in
        VALID_DISPLAY_CURRENCIES ({"USDT", "RLS", "USD"}).
        """
        if not currency:
            return False
        cur = currency.strip().upper()
        if cur not in VALID_DISPLAY_CURRENCIES:
            return False
        return await self.set(user_id, KEY_DISPLAY_CURRENCY, cur)

    # ==========================================================
    # Rows-per-page helpers
    # ==========================================================
    async def get_rows_per_page(self, user_id: int) -> int:
        """
        Return the user's preferred rows-per-page, clamped to
        MIN_ROWS_PER_PAGE..MAX_ROWS_PER_PAGE.

        Returns DEFAULT_ROWS_PER_PAGE (50) if unset or non-numeric.
        """
        raw = await self.get(user_id, KEY_ROWS_PER_PAGE)
        if not raw:
            return DEFAULT_ROWS_PER_PAGE
        try:
            n = int(raw)
        except (ValueError, TypeError):
            return DEFAULT_ROWS_PER_PAGE
        if n < MIN_ROWS_PER_PAGE:
            return MIN_ROWS_PER_PAGE
        if n > MAX_ROWS_PER_PAGE:
            return MAX_ROWS_PER_PAGE
        return n

    async def set_rows_per_page(
        self, user_id: int, count: int
    ) -> bool:
        """Set rows-per-page. Rejects values outside valid range."""
        try:
            n = int(count)
        except (ValueError, TypeError):
            return False
        if n < MIN_ROWS_PER_PAGE or n > MAX_ROWS_PER_PAGE:
            return False
        return await self.set(user_id, KEY_ROWS_PER_PAGE, str(n))

    # ==========================================================
    # Introspection
    # ==========================================================
    def __repr__(self) -> str:
        return f"UserPreferenceRepository(module={self._module!r})"


__all__ = [
    "UserPreferenceRepository",
    "KEY_FAVORITES",
    "KEY_DISPLAY_CURRENCY",
    "KEY_ROWS_PER_PAGE",
    "DEFAULT_DISPLAY_CURRENCY",
    "DEFAULT_ROWS_PER_PAGE",
    "VALID_DISPLAY_CURRENCIES",
    "MIN_ROWS_PER_PAGE",
    "MAX_ROWS_PER_PAGE",
]
