"""
Access control checker.

Combines the `role`, `form`, `condition_of`, and `form_access` tables
to answer whether a user has access to a given form. Uses an in-memory
cache with TTL to avoid hitting the database on every request.
"""
import time
from typing import Optional

from ..models.access import Role, FormAccess


class AccessChecker:
    """
    Role-based access checker with TTL cache.

    Parameters
    ----------
    db_service : DbManagerService
        The facade that exposes the access repositories.
    logger : optional
        Shared logger.
    """

    # --- Cache TTLs (seconds) ---
    USER_ENABLED_TTL = 15.0
    USER_ROLE_TTL    = 300.0
    ROLE_FORM_TTL    = 300.0

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

        # Caches — value is (timestamp_monotonic, payload)
        self._user_enabled_cache: dict[int, tuple[float, bool]] = {}
        self._user_role_cache:    dict[int, tuple[float, Optional[int]]] = {}
        self._role_form_cache:    dict[tuple[int, str],
                                       tuple[float, Optional[str]]] = {}

    # ============================================================
    # Internal helpers
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
        """
        Return True if the user is currently enabled.

        Cached with a short TTL so that disabled users are ejected from
        the application within USER_ENABLED_TTL seconds.
        """
        if not user_id:
            return False

        cached = self._user_enabled_cache.get(user_id)
        if cached and (self._now() - cached[0]) < self.USER_ENABLED_TTL:
            return cached[1]

        enabled = await self._db._user_repo.is_enabled(user_id)
        self._user_enabled_cache[user_id] = (self._now(), enabled)
        return enabled

    async def get_user_role_id(self, user_id: int) -> Optional[int]:
        """
        Return the user's role_id, or None if the user does not exist.
        """
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
    async def get_form_condition(
        self, user_id: int, form_id: str
    ) -> Optional[str]:
        """
        Return the condition name the user has for the given form, or
        None if the user has no access to it.

        The caller decides what the condition name means (e.g. "low",
        "high", or a numeric level).
        """
        if not user_id or not form_id:
            return None

        # Must be enabled
        if not await self.is_user_enabled(user_id):
            return None

        role_id = await self.get_user_role_id(user_id)
        if role_id is None:
            return None

        key = (role_id, form_id)
        cached = self._role_form_cache.get(key)
        if cached and (self._now() - cached[0]) < self.ROLE_FORM_TTL:
            return cached[1]

        row = await self._db._form_access_repo.get_full_access_one(
            role_id=role_id, form_id=form_id
        )
        condition_name = row.get("condition_name") if row else None
        self._role_form_cache[key] = (self._now(), condition_name)
        return condition_name

    async def has_access(
        self,
        user_id: int,
        form_id: str,
        required_condition: Optional[str] = None,
    ) -> bool:
        """
        Return True if the user has access to the given form.

        If `required_condition` is None, any condition counts as access.
        If `required_condition` is provided, the user's condition name
        must match it exactly.

        For complex logic (e.g. numeric levels), use get_form_condition()
        and interpret the result in the caller.
        """
        condition = await self.get_form_condition(user_id, form_id)
        if condition is None:
            return False
        if required_condition is None:
            return True
        return condition == required_condition

    async def get_accessible_forms(self, user_id: int) -> list[str]:
        """
        Return the list of form_ids the user has access to.
        """
        if not user_id:
            return []

        if not await self.is_user_enabled(user_id):
            return []

        role_id = await self.get_user_role_id(user_id)
        if role_id is None:
            return []

        rows = await self._db._form_access_repo.list_by_role(role_id)
        return [row["form_id"] for row in rows if row.get("form_id")]

    async def get_user_role(self, user_id: int) -> Optional[Role]:
        """
        Return the user's Role as a Role dataclass, or None.
        """
        role_id = await self.get_user_role_id(user_id)
        if role_id is None:
            return None
        row = await self._db._role_repo.get_by_id(role_id)
        return Role.from_row(row) if row else None

    async def list_role_forms(self, role_id: int) -> list[FormAccess]:
        """
        Return all form accesses attached to the given role, enriched
        with form_name and condition_name.
        """
        if not role_id:
            return []
        rows = await self._db._form_access_repo.get_full_access(role_id)
        return [FormAccess.from_row(row) for row in rows]

    # ============================================================
    # Cache management
    # ============================================================
    def invalidate_user(self, user_id: Optional[int] = None) -> None:
        """
        Clear the personal caches (enabled + role) for a user.

        If user_id is None, clears the entire personal caches.
        """
        if user_id is None:
            self._user_enabled_cache.clear()
            self._user_role_cache.clear()
            return
        self._user_enabled_cache.pop(user_id, None)
        self._user_role_cache.pop(user_id, None)

    def invalidate_role(self, role_id: Optional[int] = None) -> None:
        """
        Clear the role→form access cache.

        If role_id is None, clears the entire role-form cache.
        """
        if role_id is None:
            self._role_form_cache.clear()
            return
        keys = [k for k in self._role_form_cache if k[0] == role_id]
        for k in keys:
            self._role_form_cache.pop(k, None)

    def invalidate_form(self, form_id: Optional[str] = None) -> None:
        """
        Clear cache entries referring to the given form_id.

        If form_id is None, clears the entire role-form cache.
        """
        if form_id is None:
            self._role_form_cache.clear()
            return
        keys = [k for k in self._role_form_cache if k[1] == form_id]
        for k in keys:
            self._role_form_cache.pop(k, None)

    def clear_cache(self) -> None:
        """Clear every cache."""
        self._user_enabled_cache.clear()
        self._user_role_cache.clear()
        self._role_form_cache.clear()
