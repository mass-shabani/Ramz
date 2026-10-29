"""
Access control checker.

Uses the `form_access` table (role × form → level) to answer whether
a user has access to a given form. Caches results with a TTL.

`level` semantics:
    0     = Closed (no access)
    ≥1    = Open; higher values indicate privileged levels
"""
import time
from typing import Optional

from ..models.access import Role, FormAccess


class AccessChecker:

    # --- Cache TTLs (seconds) ---
    USER_ENABLED_TTL = 15.0
    USER_ROLE_TTL    = 60.0
    ROLE_FORM_TTL    = 60.0

    def __init__(self, db_service, logger=None, debug=False):
        self._db = db_service
        self._logger = logger
        self._debug = bool(debug)

        # (timestamp, role_id or None)
        self._user_role_cache: dict[int, tuple[float, Optional[str]]] = {}
        # (role_id, form_id) → (timestamp, level: int)  ; missing = no grant
        self._role_form_cache: dict[tuple[str, str], tuple[float, int]] = {}
        # (timestamp, enabled)
        self._user_enabled_cache: dict[int, tuple[float, bool]] = {}

    # ============================================================
    # Internal
    # ============================================================
    def _now(self) -> float:
        return time.monotonic()

    def _log(self, message, level="INFO"):
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="database")
            except Exception:
                pass

    # ============================================================
    # User state
    # ============================================================
    async def is_user_enabled(self, user_id: int) -> bool:
        if not user_id:
            return False
        cached = self._user_enabled_cache.get(user_id)
        if cached and (self._now() - cached[0]) < self.USER_ENABLED_TTL:
            return cached[1]
        enabled = await self._db._user_repo.is_enabled(user_id)
        self._user_enabled_cache[user_id] = (self._now(), enabled)
        return enabled

    async def get_user_role_id(self, user_id: int) -> Optional[str]:
        if not user_id:
            return None
        cached = self._user_role_cache.get(user_id)
        if cached and (self._now() - cached[0]) < self.USER_ROLE_TTL:
            return cached[1]
        user = await self._db._user_repo.get_by_id(user_id)
        role_id = user.role_id if user else None
        self._user_role_cache[user_id] = (self._now(), role_id)
        return role_id

    # ============================================================
    # Access resolution
    # ============================================================
    async def get_form_level_by_role(
        self, role_id: str, form_id: str
    ) -> int:
        """
        Return the level the given role has for the given form.
        0 if no grant exists.
        """
        if not role_id or not form_id:
            return 0
        key = (role_id, form_id)
        cached = self._role_form_cache.get(key)
        if cached and (self._now() - cached[0]) < self.ROLE_FORM_TTL:
            return cached[1]
        row = await self._db._form_access_repo.get(role_id, form_id)
        level = int(row.get("level", 0)) if row else 0
        self._role_form_cache[key] = (self._now(), level)
        return level

    async def get_form_level(
        self, user_id: int, form_id: str
    ) -> int:
        """
        Return the level the user has for the given form.
        0 if user is disabled, has no role, or has no grant.
        """
        if not user_id or not form_id:
            return 0
        if not await self.is_user_enabled(user_id):
            return 0
        role_id = await self.get_user_role_id(user_id)
        if role_id is None:
            return 0
        return await self.get_form_level_by_role(role_id, form_id)

    async def has_access(
        self,
        user_id: int,
        form_id: str,
        min_level: int = 1,
        required_condition: Optional[str] = None,   # deprecated, ignored
    ) -> bool:
        """
        Return True if user's level for this form is >= min_level.

        A level of 0 (Closed) always returns False regardless of
        min_level (0 is treated as "no access").
        """
        if min_level <= 0:
            min_level = 1
        level = await self.get_form_level(user_id, form_id)
        return level >= min_level

    async def has_role_access(
        self,
        role_id: Optional[str],
        form_id: str,
        min_level: int = 1,
        required_condition: Optional[str] = None,   # deprecated, ignored
    ) -> bool:
        """
        Return True if role's level for this form is >= min_level.
        """
        if min_level <= 0:
            min_level = 1
        if role_id is None or not form_id:
            return False
        level = await self.get_form_level_by_role(role_id, form_id)
        return level >= min_level

    async def get_form_condition(
        self, user_id: int, form_id: str
    ) -> Optional[str]:
        """
        DEPRECATED: use get_form_level().

        Returns "Open" if level >= 1, "Closed" if level 0 with a grant,
        or None if no grant exists.
        """
        if not user_id or not form_id:
            return None
        if not await self.is_user_enabled(user_id):
            return None
        role_id = await self.get_user_role_id(user_id)
        if role_id is None:
            return None
        row = await self._db._form_access_repo.get(role_id, form_id)
        if not row:
            return None
        level = int(row.get("level", 0))
        return "Open" if level >= 1 else "Closed"

    async def get_form_condition_by_role(
        self, role_id: str, form_id: str
    ) -> Optional[str]:
        """
        DEPRECATED: use get_form_level_by_role().
        """
        if not role_id or not form_id:
            return None
        row = await self._db._form_access_repo.get(role_id, form_id)
        if not row:
            return None
        level = int(row.get("level", 0))
        return "Open" if level >= 1 else "Closed"

    async def get_accessible_forms(self, user_id: int) -> list[str]:
        """Return the list of form_ids where the user's level >= 1."""
        if not user_id:
            return []
        if not await self.is_user_enabled(user_id):
            return []
        role_id = await self.get_user_role_id(user_id)
        if role_id is None:
            return []
        rows = await self._db._form_access_repo.list_by_role(role_id)
        return [
            row["form_id"]
            for row in rows
            if row.get("form_id") and int(row.get("level", 0)) >= 1
        ]

    async def get_user_role(self, user_id: int) -> Optional[Role]:
        role_id = await self.get_user_role_id(user_id)
        if role_id is None:
            return None
        row = await self._db._role_repo.get_by_id(role_id)
        return Role.from_row(row) if row else None

    async def get_user_role_rank(self, user_id: int) -> int:
        """
        Return the rank of the user's role, or 0 if unknown.
        Used for rank-based authorization (see admin_panel).
        """
        if not user_id:
            return 0
        role_id = await self.get_user_role_id(user_id)
        if role_id is None:
            return 0
        role = await self._db._role_repo.get_by_id(role_id)
        if not role:
            return 0
        return int(role.get("rank") or 0)

    async def list_role_forms(self, role_id: str) -> list[FormAccess]:
        if not role_id:
            return []
        rows = await self._db._form_access_repo.get_full_access(role_id)
        return [FormAccess.from_row(row) for row in rows]

    # ============================================================
    # Cache management
    # ============================================================
    def invalidate_user(self, user_id: Optional[int] = None) -> None:
        if user_id is None:
            self._user_enabled_cache.clear()
            self._user_role_cache.clear()
            return
        self._user_enabled_cache.pop(user_id, None)
        self._user_role_cache.pop(user_id, None)

    def invalidate_role(self, role_id: Optional[str] = None) -> None:
        if role_id is None:
            self._role_form_cache.clear()
            return
        keys = [k for k in self._role_form_cache if k[0] == role_id]
        for k in keys:
            self._role_form_cache.pop(k, None)

    def invalidate_form(self, form_id: Optional[str] = None) -> None:
        if form_id is None:
            self._role_form_cache.clear()
            return
        keys = [k for k in self._role_form_cache if k[1] == form_id]
        for k in keys:
            self._role_form_cache.pop(k, None)

    def clear_cache(self) -> None:
        self._user_enabled_cache.clear()
        self._user_role_cache.clear()
        self._role_form_cache.clear()
