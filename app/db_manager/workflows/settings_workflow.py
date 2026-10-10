"""
Settings workflow.

Handles account settings operations:

    • change_password      — change the user's password
    • update_email         — change the primary email
    • update_phone         — change the primary phone
    • enable_2fa           — turn on two-factor authentication
    • disable_2fa          — turn off two-factor authentication

Each method is atomic where it matters, logs the corresponding
activity, and never returns a partial state.
"""
import json
from typing import Optional

from ..security.password import (
    hash_password,
    verify_password,
    needs_rehash,
)


class SettingsError(Exception):
    """
    Raised when a settings operation cannot proceed.

    The `code` attribute indicates the reason:
        • "invalid_password"      — current password is wrong
        • "weak_password"         — new password too short
        • "same_password"         — new password equals current
        • "user_not_found"        — user_id does not exist
        • "invalid_data"          — missing or malformed input
        • "2fa_already_enabled"   — enable called when already on
        • "2fa_not_enabled"       — disable called when already off
        • "internal_error"        — anything else
    """
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


class SettingsWorkflow:

    MIN_PASSWORD_LENGTH = 8

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _log(self, message, level="INFO"):
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="database")
            except Exception:
                pass

    async def _log_activity(
        self,
        user_id: int,
        type_name: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Best-effort activity logging — never raises."""
        try:
            await self._db._activity_repo.log(
                user_id=user_id,
                type_name=type_name,
                ip_address=ip,
                user_agent=user_agent,
            )
        except Exception as exc:
            self._log(f"activity log failed: {exc}", level="WARNING")

    # ============================================================
    # Password
    # ============================================================
    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Change the user's password.

        Raises
        ------
        SettingsError
            with codes: invalid_password | weak_password |
            same_password | user_not_found | internal_error
        """
        if not user_id or not current_password or not new_password:
            raise SettingsError("invalid_data")

        if len(new_password) < self.MIN_PASSWORD_LENGTH:
            raise SettingsError("weak_password")

        if current_password == new_password:
            raise SettingsError("same_password")

        # Fetch user with password hash
        user = await self._db._user_repo.get_by_id(
            user_id, include_password=True
        )
        if user is None:
            raise SettingsError("user_not_found")

        # Verify current password
        if not user.password_hash or not verify_password(
            current_password, user.password_hash
        ):
            raise SettingsError("invalid_password")

        # Hash and save
        try:
            new_hash = hash_password(new_password)
            ok = await self._db._user_repo.update_password_hash(
                user_id, new_hash
            )
            if not ok:
                raise SettingsError("internal_error", "update failed")
        except SettingsError:
            raise
        except Exception as exc:
            self._log(f"change_password failed: {exc}", level="ERROR")
            raise SettingsError("internal_error", str(exc))

        await self._log_activity(
            user_id, "password_change", ip, user_agent
        )
        return True

    # ============================================================
    # Email
    # ============================================================
    async def update_email(
        self,
        user_id: int,
        new_email: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Change the primary email for a user.

        If another user already uses the email, raises SettingsError
        with code "email_exists". Verification is reset.
        """
        if not user_id or not new_email:
            raise SettingsError("invalid_data")

        user = await self._db._user_repo.get_by_id(user_id)
        if user is None:
            raise SettingsError("user_not_found")

        # Check for conflict
        existing = await self._db._email_repo.get_by_address(new_email)
        if existing and int(existing.get("email_id", 0)) != (user.email_id or 0):
            raise SettingsError("email_exists")

        try:
            if user.email_id:
                # Update existing email row (resets verification)
                ok = await self._db._email_repo.update_address(
                    user.email_id, new_email
                )
                if not ok:
                    raise SettingsError("internal_error", "update failed")
            else:
                # User has no email yet — create one
                people = await self._db._people_repo.get_by_id(user.people_id)
                contact_id = int(people["contact_id"]) if people else 0
                if not contact_id:
                    raise SettingsError(
                        "internal_error", "contact not found"
                    )
                new_id = await self._db._email_repo.create(
                    contact_id=contact_id,
                    email_address=new_email,
                    is_verified=False,
                )
                if not new_id:
                    raise SettingsError(
                        "internal_error", "create failed"
                    )
                await self._db._user_repo.update_email_id(user_id, new_id)
        except SettingsError:
            raise
        except Exception as exc:
            self._log(f"update_email failed: {exc}", level="ERROR")
            raise SettingsError("internal_error", str(exc))

        await self._log_activity(
            user_id, "profile_update", ip, user_agent
        )
        return True

    # ============================================================
    # Phone
    # ============================================================
    async def update_phone(
        self,
        user_id: int,
        new_phone: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Change the primary phone for a user.

        Verification is reset. If no phone exists, one is created.
        """
        if not user_id or not new_phone:
            raise SettingsError("invalid_data")

        user = await self._db._user_repo.get_by_id(user_id)
        if user is None:
            raise SettingsError("user_not_found")

        # Check for conflict
        existing = await self._db._phone_repo.get_by_number(new_phone)
        if existing and int(existing.get("phone_id", 0)) != (user.phone_id or 0):
            raise SettingsError("phone_exists")

        try:
            if user.phone_id:
                ok = await self._db._phone_repo.update_number(
                    user.phone_id, new_phone
                )
                if not ok:
                    raise SettingsError("internal_error", "update failed")
            else:
                people = await self._db._people_repo.get_by_id(user.people_id)
                contact_id = int(people["contact_id"]) if people else 0
                if not contact_id:
                    raise SettingsError(
                        "internal_error", "contact not found"
                    )
                new_id = await self._db._phone_repo.create(
                    contact_id=contact_id,
                    phone_number=new_phone,
                    phone_type="mobile",
                    is_verified=False,
                )
                if not new_id:
                    raise SettingsError(
                        "internal_error", "create failed"
                    )
                await self._db._user_repo.update_phone_id(user_id, new_id)
        except SettingsError:
            raise
        except Exception as exc:
            self._log(f"update_phone failed: {exc}", level="ERROR")
            raise SettingsError("internal_error", str(exc))

        await self._log_activity(
            user_id, "profile_update", ip, user_agent
        )
        return True

    # ============================================================
    # 2FA
    # ============================================================
    async def enable_2fa(
        self,
        user_id: int,
        secret: str,
        backup_codes: list,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Enable two-factor authentication.

        Parameters
        ----------
        user_id : int
        secret : str
            The TOTP secret (base32). Must be non-empty.
        backup_codes : list[str]
            A list of one-time codes. Stored as a JSON string.
        """
        if not user_id or not secret or not backup_codes:
            raise SettingsError("invalid_data")

        user = await self._db._user_repo.get_by_id(user_id)
        if user is None:
            raise SettingsError("user_not_found")

        if user.two_factor_enabled:
            raise SettingsError("2fa_already_enabled")

        try:
            codes_json = json.dumps(list(backup_codes))
            ok = await self._db._user_repo.set_2fa(
                user_id=user_id,
                enabled=True,
                secret=secret,
                backup_codes=codes_json,
            )
            if not ok:
                raise SettingsError("internal_error", "update failed")
        except SettingsError:
            raise
        except Exception as exc:
            self._log(f"enable_2fa failed: {exc}", level="ERROR")
            raise SettingsError("internal_error", str(exc))

        await self._log_activity(user_id, "2fa_enabled", ip, user_agent)
        return True

    async def disable_2fa(
        self,
        user_id: int,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Disable two-factor authentication and clear the secret and
        backup codes.
        """
        if not user_id:
            raise SettingsError("invalid_data")

        user = await self._db._user_repo.get_by_id(user_id)
        if user is None:
            raise SettingsError("user_not_found")

        if not user.two_factor_enabled:
            raise SettingsError("2fa_not_enabled")

        try:
            ok = await self._db._user_repo.set_2fa(
                user_id=user_id,
                enabled=False,
            )
            if not ok:
                raise SettingsError("internal_error", "update failed")
        except SettingsError:
            raise
        except Exception as exc:
            self._log(f"disable_2fa failed: {exc}", level="ERROR")
            raise SettingsError("internal_error", str(exc))

        await self._log_activity(user_id, "2fa_disabled", ip, user_agent)
        return True
