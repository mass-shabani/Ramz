"""
Profile workflow.

Aggregates a user's complete profile from multiple tables, and provides
update operations for personal and contact information.

Read operations combine data from:
    user, people, role, subscription, email, phone, post_address

Update operations are atomic — either all changes in a call succeed or
none do.
"""
from datetime import datetime
from typing import Optional

from ..models.profile import Profile


class ProfileWorkflow:

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _log(self, message, level="INFO"):
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="database")
            except Exception:
                pass

    # ============================================================
    # Reads
    # ============================================================
    async def get_full_profile(self, user_id: int) -> Optional[Profile]:
        """
        Return the complete profile of a user.

        Uses multiple small queries instead of one big JOIN, which keeps
        each repository independent and easy to test.

        Returns None if the user does not exist.
        """
        if not user_id:
            return None

        # 1. Base user row (with role_name, subscription_name, email, phone)
        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return None

        # 2. People row (for contact_id and personal fields)
        people = await self._db._people_repo.get_by_id(user.people_id)

        # 3. Full email row (for is_verified)
        email_row = None
        if user.email_id:
            email_row = await self._db._email_repo.get_by_id(user.email_id)

        # 4. Full phone row (for is_verified)
        phone_row = None
        if user.phone_id:
            phone_row = await self._db._phone_repo.get_by_id(user.phone_id)

        # 5. Primary address (via people.contact_id)
        address_row = None
        if people and people.get("contact_id"):
            address_row = await self._db._address_repo.get_primary(
                people["contact_id"]
            )

        # 6. Build Profile
        return Profile(
            # user
            user_id=user.user_id,
            username=user.username,
            enabled=user.enabled,
            xp_points=user.xp_points,
            two_factor_enabled=user.two_factor_enabled,
            created_at=user.created_at,

            # people
            people_id=user.people_id,
            contact_id=int(people["contact_id"]) if people else 0,
            first_name=user.first_name,
            last_name=user.last_name,
            national_code=people.get("national_code") if people else None,
            birth_date=_parse_date(people.get("birth_date")) if people else None,
            gender=people.get("gender") if people else None,

            # role
            role_id=user.role_id,
            role_name=user.role_name or "",

            # subscription
            subscription_id=user.subscription_id,
            subscription_name=user.subscription_name,

            # email
            email_id=user.email_id,
            email=user.email,
            email_verified=bool(email_row and email_row.get("is_verified")),

            # phone
            phone_id=user.phone_id,
            phone=user.phone,
            phone_verified=bool(phone_row and phone_row.get("is_verified")),

            # address
            address_id=int(address_row["address_id"]) if address_row else None,
            address_line1=address_row.get("address_line1") if address_row else None,
            address_line2=address_row.get("address_line2") if address_row else None,
            city=address_row.get("city") if address_row else None,
            state_province=address_row.get("state_province") if address_row else None,
            postal_code=address_row.get("postal_code") if address_row else None,
            country=address_row.get("country") if address_row else None,
        )

    # ============================================================
    # Updates
    # ============================================================
    async def update_personal_info(
        self, user_id: int, data: dict
    ) -> bool:
        """
        Update personal information (people table).

        Accepted keys: first_name, last_name, national_code,
        birth_date, gender.

        Empty values are ignored (no-op). Returns True on success.
        """
        if not user_id or not data:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user or not user.people_id:
            return False

        # Filter to non-empty fields
        clean = {k: v for k, v in data.items() if v not in (None, "")}
        if not clean:
            return False

        return await self._db._people_repo.update(user.people_id, **clean)

    async def update_contact_info(
        self, user_id: int, data: dict
    ) -> bool:
        """
        Update contact information (email, phone, address).

        Accepted keys:
            • email              — new email address
            • phone              — new phone number
            • address_line1, address_line2, city, state_province,
              postal_code, country — new address fields

        Each sub-entity updates independently inside a single
        transaction. If any fails, the entire update rolls back.

        Returns True on success, False otherwise.
        """
        if not user_id or not data:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0

        new_email   = data.get("email")
        new_phone   = data.get("phone")
        address_fields = {
            k: v for k, v in data.items()
            if k in ("address_line1", "address_line2", "city",
                     "state_province", "postal_code", "country")
            and v not in (None, "")
        }

        try:
            conn = self._db.connection()
            async with conn.begin_transaction():
                # --- Email ---
                if new_email and user.email_id:
                    await self._db._email_repo.update_address(
                        user.email_id, new_email
                    )

                # --- Phone ---
                if new_phone and user.phone_id:
                    await self._db._phone_repo.update_number(
                        user.phone_id, new_phone
                    )

                # --- Address ---
                if address_fields and contact_id:
                    primary = await self._db._address_repo.get_primary(contact_id)
                    if primary:
                        await self._db._address_repo.update(
                            int(primary["address_id"]), **address_fields
                        )
                    else:
                        # No address yet — create one
                        await self._db._address_repo.create(
                            contact_id=contact_id,
                            address_line1=address_fields.get("address_line1", ""),
                            address_line2=address_fields.get("address_line2"),
                            city=address_fields.get("city"),
                            state_province=address_fields.get("state_province"),
                            postal_code=address_fields.get("postal_code"),
                            country=address_fields.get("country", "Iran"),
                        )
            return True

        except Exception as exc:
            self._log(f"update_contact_info failed: {exc}", level="ERROR")
            return False


# --------------------------------------------------------------
# Helpers
# --------------------------------------------------------------
def _parse_date(value) -> Optional[datetime]:
    """Parse a date-like value (SQLite may return a string)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None
