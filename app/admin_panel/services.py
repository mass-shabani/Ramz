"""
Admin Panel Service

Facade for admin panel operations.
"""


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

        Returns
        -------
        tuple (ok: bool, code: Optional[str])
        """
        if int(target_user_id) == int(current_user_id):
            return False, "cannot_modify_self"

        target = await self.db.get_user_by_id(target_user_id)
        if not target:
            return False, "user_not_found"

        if target.role_id == "super-admin":
            return False, "cannot_modify_super_admin"

        if new_role_id == "super-admin":
            return False, "cannot_promote_to_super_admin"

        ok, code = await self.db.admin_set_user_role(
            target_user_id, new_role_id
        )
        return ok, code

    async def toggle_user(
        self, target_user_id, enabled, current_user_id
    ):
        """Enable/disable a user. Returns (ok, code)."""
        if int(target_user_id) == int(current_user_id):
            return False, "cannot_modify_self"

        target = await self.db.get_user_by_id(target_user_id)
        if not target:
            return False, "user_not_found"

        if target.role_id == "super-admin":
            return False, "cannot_modify_super_admin"

        ok = await self.db.admin_toggle_user(target_user_id, enabled)
        return (ok, None) if ok else (False, "internal_error")

    async def reset_password(self, target_user_id, current_user_id):
        """Reset a user's password. Returns (ok, temp_password, code)."""
        if int(target_user_id) == int(current_user_id):
            return False, None, "cannot_modify_self"

        target = await self.db.get_user_by_id(target_user_id)
        if not target:
            return False, None, "user_not_found"

        if target.role_id == "super-admin":
            return False, None, "cannot_modify_super_admin"

        ok, temp_password = await self.db.admin_reset_password(
            target_user_id
        )
        if not ok:
            return False, None, "internal_error"
        return True, temp_password, None
