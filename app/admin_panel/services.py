"""
Admin Panel Service

Facade for admin panel operations.
"""

import re


def _slugify_form_name(name):
    """
    Turn a human-readable form name into a stable form_id.

    Examples:
        "Admin Panel Access"   → "admin.panel.access"
        "Login Page"           → "login.page"
        "Test Form (v2)"       → "test.form.v2"
        ""                     → ""
    """
    if not name:
        return ""
    slug = re.sub(r'[^a-z0-9._]+', '.', name.lower().strip())
    slug = re.sub(r'\.+', '.', slug).strip('.')
    return slug


class AdminPanelService:
    """
    Facade for admin panel operations.
    """

    def __init__(self, db_service, template_service, logger=None):
        self.db = db_service
        self.template_service = template_service
        self.logger = logger

    def _log(self, message, level="INFO"):
        if self.logger:
            try:
                self.logger.log(message, level=level, tag="admin")
            except Exception:
                pass

    # ============================================================
    # Users
    # ============================================================
    async def set_user_role(
        self, target_user_id, new_role_id, current_user_id
    ):
        """
        Change a user's role (by role_id).

        Authorization is purely rank-based:
          • current.rank > target.rank      (cannot modify equal/higher rank)
          • current.rank > new_role.rank    (cannot promote to equal/higher rank)

        These two rules automatically cover:
          • self-modification (equal rank)
          • super-admin target (max rank, no one above)
          • promote-to-super-admin (equal rank for non-super-admins)

        Returns (ok: bool, code: Optional[str]).
        """
        target = await self.db.get_user_by_id(target_user_id)
        if not target:
            return False, "user_not_found"

        new_role = await self.db._role_repo.get_by_id(new_role_id)
        if not new_role:
            return False, "role_not_found"

        current_rank = await self.db.get_user_rank(current_user_id)
        target_rank = int(target.role_rank or 0)
        new_role_rank = int(new_role.get("rank") or 0)

        if current_rank <= target_rank:
            return False, "insufficient_rank"

        if current_rank <= new_role_rank:
            return False, "insufficient_rank"

        ok, code = await self.db.admin_set_user_role(
            target_user_id, new_role_id
        )
        return ok, code

    async def toggle_user(
        self, target_user_id, enabled, current_user_id
    ):
        """
        Enable/disable a user. Returns (ok, code).

        Authorization is purely rank-based:
          • current.rank > target.rank
        """
        target = await self.db.get_user_by_id(target_user_id)
        if not target:
            return False, "user_not_found"

        current_rank = await self.db.get_user_rank(current_user_id)
        target_rank = int(target.role_rank or 0)
        if current_rank <= target_rank:
            return False, "insufficient_rank"

        ok = await self.db.admin_toggle_user(target_user_id, enabled)
        return (ok, None) if ok else (False, "internal_error")

    async def reset_password(self, target_user_id, current_user_id):
        """
        Reset a user's password. Returns (ok, temp_password, code).

        Authorization is purely rank-based:
          • current.rank > target.rank
        """
        target = await self.db.get_user_by_id(target_user_id)
        if not target:
            return False, None, "user_not_found"

        current_rank = await self.db.get_user_rank(current_user_id)
        target_rank = int(target.role_rank or 0)
        if current_rank <= target_rank:
            return False, None, "insufficient_rank"

        ok, temp_password = await self.db.admin_reset_password(
            target_user_id
        )
        if not ok:
            return False, None, "internal_error"
        return True, temp_password, None

    # ============================================================
    # Forms
    # ============================================================
    async def create_form(
        self, form_id, form_name, description, enabled, current_user_id
    ):
        """
        Create a new form.

        If form_id is empty, it is auto-generated from form_name
        (lowercased, non-alphanumeric → dots, collapsed).

        Returns
        -------
        tuple (ok: bool, final_form_id: Optional[str], code: Optional[str])
        """
        name = (form_name or "").strip()
        if not name:
            return False, None, "invalid_data"

        # Auto-gen form_id from name if not provided
        final_id = (form_id or "").strip()
        if not final_id:
            final_id = _slugify_form_name(name)
            if not final_id:
                return False, None, "invalid_data"

        # Check form_id conflict
        existing = await self.db.admin_get_form(final_id)
        if existing:
            return False, None, "form_id_exists"

        # Check form_name conflict (schema has UNIQUE on form_name)
        try:
            existing_name = await self.db._form_repo.get_by_name(name)
        except Exception:
            existing_name = None
        if existing_name:
            return False, None, "form_name_exists"

        ok = await self.db.admin_create_form(
            form_id=final_id,
            form_name=name,
            description=(description or "").strip(),
            enabled=bool(enabled),
        )
        if not ok:
            return False, None, "internal_error"

        self.db.invalidate_form_cache(final_id)
        return True, final_id, None

    async def update_form(
        self, form_id, form_name, description, enabled, current_user_id
    ):
        """
        Update an existing form.

        Returns (ok: bool, code: Optional[str]).
        """
        fid = (form_id or "").strip()
        name = (form_name or "").strip()
        if not fid or not name:
            return False, "invalid_data"

        existing = await self.db.admin_get_form(fid)
        if not existing:
            return False, "form_not_found"

        # Check form_name conflict on OTHER forms
        try:
            existing_name = await self.db._form_repo.get_by_name(name)
        except Exception:
            existing_name = None
        if existing_name and existing_name.get("form_id") != fid:
            return False, "form_name_exists"

        ok = await self.db.admin_update_form(
            form_id=fid,
            form_name=name,
            description=(description or "").strip(),
            enabled=bool(enabled),
        )
        if not ok:
            return False, "internal_error"

        self.db.invalidate_form_cache(fid)
        return True, None

    async def delete_form(self, form_id, current_user_id):
        """
        Delete a form.

        Returns (ok: bool, code: Optional[str], grants_count: int).
        If grants_count > 0, code is "form_has_grants".
        """
        fid = (form_id or "").strip()
        if not fid:
            return False, "invalid_data", 0

        existing = await self.db.admin_get_form(fid)
        if not existing:
            return False, "form_not_found", 0

        grants = await self.db.admin_form_grant_count(fid)
        if grants > 0:
            return False, "form_has_grants", grants

        ok = await self.db.admin_delete_form(fid)
        if not ok:
            return False, "internal_error", 0

        self.db.invalidate_form_cache(fid)
        return True, None, 0

    # ============================================================
    # Access Grants
    # ============================================================
    async def create_grant(
        self, role_id, form_id, level, current_user_id
    ):
        """
        Create a new grant with numeric level (0 = closed, ≥1 = open).

        Returns (ok: bool, code: Optional[str]).
        """
        rid = (role_id or "").strip()
        fid = (form_id or "").strip()

        if not rid or not fid:
            return False, "invalid_data"

        try:
            lvl = int(level)
        except (TypeError, ValueError):
            return False, "invalid_data"
        if lvl < 0:
            return False, "invalid_data"

        if rid == "super-admin":
            return False, "cannot_modify_super_admin"

        role = await self.db._role_repo.get_by_id(rid)
        if not role:
            return False, "role_not_found"

        form = await self.db.admin_get_form(fid)
        if not form:
            return False, "form_not_found"

        ok, code = await self.db.admin_create_grant(rid, fid, lvl)
        return ok, code

    async def update_grant_level(
        self, role_id, form_id, new_level, current_user_id
    ):
        """
        Update the level of an existing grant.

        Returns (ok: bool, code: Optional[str]).
        """
        rid = (role_id or "").strip()
        fid = (form_id or "").strip()

        if not rid or not fid:
            return False, "invalid_data"

        try:
            lvl = int(new_level)
        except (TypeError, ValueError):
            return False, "invalid_data"
        if lvl < 0:
            return False, "invalid_data"

        if rid == "super-admin":
            return False, "cannot_modify_super_admin"

        existing = await self.db.admin_get_grant(rid, fid)
        if not existing:
            return False, "grant_not_found"

        ok = await self.db.admin_update_grant_level(rid, fid, lvl)
        return (True, None) if ok else (False, "internal_error")

    async def delete_grant(self, role_id, form_id, current_user_id):
        """
        Delete a grant.

        Returns (ok: bool, code: Optional[str]).
        """
        rid = (role_id or "").strip()
        fid = (form_id or "").strip()
        if not rid or not fid:
            return False, "invalid_data"

        if rid == "super-admin":
            return False, "cannot_modify_super_admin"

        existing = await self.db.admin_get_grant(rid, fid)
        if not existing:
            return False, "grant_not_found"

        ok = await self.db.admin_delete_grant(rid, fid)
        return (True, None) if ok else (False, "internal_error")
