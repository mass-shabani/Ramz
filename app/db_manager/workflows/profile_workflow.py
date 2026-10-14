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

    # ============================================================
    # Multi-value contact management
    # ============================================================
    async def list_contact_channels(self, user_id: int) -> dict:
        """
        Return all emails, phones, and addresses for the user's contact.

        Each email/phone entry has an `is_primary` flag that is True
        only if it matches `user.email_id` / `user.phone_id`.

        Returns
        -------
        dict
            {
                "emails":    [{"email_id", "email_address", "is_verified", "is_primary"}, ...],
                "phones":    [{"phone_id", "phone_number", "phone_type", "is_verified", "is_primary"}, ...],
                "addresses": [{"address_id", ...}, ...],
            }
        """
        empty = {"emails": [], "phones": [], "addresses": []}
        if not user_id:
            return empty

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return empty

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return empty

        # Emails
        emails = await self._db._email_repo.list_by_contact(contact_id)
        for e in emails:
            e["is_primary"] = (int(e.get("email_id") or 0) == (user.email_id or 0))

        # Phones (with type name)
        phones = await self._db._phone_repo.list_by_contact_with_type(contact_id)
        for p in phones:
            p["is_primary"] = (int(p.get("phone_id") or 0) == (user.phone_id or 0))
            # Normalize field name for backward-compat with template
            p["phone_type"] = p.get("type_name") or "mobile"

        # Addresses (with type name)
        addresses = await self._db._address_repo.list_by_contact_with_type(contact_id)
        for a in addresses:
            a["address_type"] = a.get("type_name") or "home"

        return {
            "emails":    emails,
            "phones":    phones,
            "addresses": addresses,
        }

    async def add_email(self, user_id: int, email_address: str) -> bool:
        """
        Add a new email address to the user's contact.

        Important
        ---------
        The new email is NOT automatically assigned as the user's
        primary. The user must explicitly call set_primary_email().
        This avoids an accidental first-come-first-served assignment
        and matches the UX expectation that "primary" is a deliberate
        choice made in the account settings page.

        Returns True on success, False if the email already exists or
        on any error.
        """
        if not user_id or not email_address:
            return False

        # Global conflict check
        existing = await self._db._email_repo.get_by_address(email_address)
        if existing:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        try:
            new_id = await self._db._email_repo.create(
                contact_id=contact_id,
                email_address=email_address,
                is_verified=False,
            )
            return bool(new_id)
        except Exception as exc:
            self._log(f"add_email failed: {exc}", level="ERROR")
            return False

    async def remove_email(self, user_id: int, email_id: int) -> tuple:
        """
        Remove an email from the user's contact.

        Rules:
            • Cannot remove the primary email.
            • Cannot remove the last remaining email.

        Returns
        -------
        tuple (ok: bool, reason: str)
            reason is one of: "ok", "is_primary", "is_last", "not_found"
        """
        if not user_id or not email_id:
            return False, "not_found"

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False, "not_found"

        if int(email_id) == int(user.email_id or 0):
            return False, "is_primary"

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False, "not_found"

        target = await self._db._email_repo.get_by_id(email_id)
        if not target or int(target.get("contact_id", 0)) != contact_id:
            return False, "not_found"

        all_emails = await self._db._email_repo.list_by_contact(contact_id)
        if len(all_emails) <= 1:
            return False, "is_last"

        try:
            ok = await self._db._email_repo.delete(email_id)
            return (ok, "ok" if ok else "not_found")
        except Exception as exc:
            self._log(f"remove_email failed: {exc}", level="ERROR")
            return False, "not_found"

    async def set_primary_email(self, user_id: int, email_id: int) -> bool:
        """
        Explicitly set the given email as the user's primary email.
        Only this method can change user.email_id.
        """
        if not user_id or not email_id:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        target = await self._db._email_repo.get_by_id(email_id)
        if not target or int(target.get("contact_id", 0)) != contact_id:
            return False

        try:
            return await self._db._user_repo.update_email_id(user_id, email_id)
        except Exception as exc:
            self._log(f"set_primary_email failed: {exc}", level="ERROR")
            return False

    async def add_phone(
        self, user_id: int, phone_number: str, phone_type: str = "mobile"
    ) -> bool:
        """
        Add a new phone number to the user's contact.

        Important
        ---------
        Same as add_email: the new phone is NOT auto-assigned as
        primary. The user must explicitly call set_primary_phone().
        """
        if not user_id or not phone_number:
            return False

        existing = await self._db._phone_repo.get_by_number(phone_number)
        if existing:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        # Resolve type name → id (fallback to "mobile")
        type_row = None
        try:
            type_row = await self._db._phone_type_repo.get_by_name(phone_type)
        except Exception:
            pass
        if not type_row:
            try:
                type_row = await self._db._phone_type_repo.get_by_name("mobile")
            except Exception:
                pass
        phone_type_id = int(type_row["phone_type_id"]) if type_row else 1

        try:
            new_id = await self._db._phone_repo.create(
                contact_id=contact_id,
                phone_number=phone_number,
                phone_type_id=phone_type_id,
                is_verified=False,
            )
            return bool(new_id)
        except Exception as exc:
            self._log(f"add_phone failed: {exc}", level="ERROR")
            return False

    async def remove_phone(self, user_id: int, phone_id: int) -> tuple:
        """
        Remove a phone. Same rules as remove_email.
        """
        if not user_id or not phone_id:
            return False, "not_found"

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False, "not_found"

        if int(phone_id) == int(user.phone_id or 0):
            return False, "is_primary"

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False, "not_found"

        target = await self._db._phone_repo.get_by_id(phone_id)
        if not target or int(target.get("contact_id", 0)) != contact_id:
            return False, "not_found"

        all_phones = await self._db._phone_repo.list_by_contact(contact_id)
        if len(all_phones) <= 1:
            return False, "is_last"

        try:
            ok = await self._db._phone_repo.delete(phone_id)
            return (ok, "ok" if ok else "not_found")
        except Exception as exc:
            self._log(f"remove_phone failed: {exc}", level="ERROR")
            return False, "not_found"

    async def set_primary_phone(self, user_id: int, phone_id: int) -> bool:
        """Explicitly set the given phone as primary."""
        if not user_id or not phone_id:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        target = await self._db._phone_repo.get_by_id(phone_id)
        if not target or int(target.get("contact_id", 0)) != contact_id:
            return False

        try:
            return await self._db._user_repo.update_phone_id(user_id, phone_id)
        except Exception as exc:
            self._log(f"set_primary_phone failed: {exc}", level="ERROR")
            return False

    # ============================================================
    # Multi-address management
    # ============================================================
    async def add_address(
        self,
        user_id: int,
        address_line1: str,
        address_line2: Optional[str] = None,
        city: Optional[str] = None,
        state_province: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: str = "Iran",
        address_type: str = "home",
    ) -> bool:
        """
        Add a new address to the user's contact.

        Addresses have no "primary" concept in the current schema —
        they are a plain list. The caller manages them freely.
        """
        if not user_id or not address_line1:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        # Resolve type name → id (fallback to "home")
        type_row = None
        try:
            type_row = await self._db._address_type_repo.get_by_name(address_type)
        except Exception:
            pass
        if not type_row:
            try:
                type_row = await self._db._address_type_repo.get_by_name("home")
            except Exception:
                pass
        address_type_id = int(type_row["address_type_id"]) if type_row else 1

        try:
            new_id = await self._db._address_repo.create(
                contact_id=contact_id,
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                state_province=state_province,
                postal_code=postal_code,
                country=country,
                address_type_id=address_type_id,
            )
            return bool(new_id)
        except Exception as exc:
            self._log(f"add_address failed: {exc}", level="ERROR")
            return False

    async def update_address(
        self, user_id: int, address_id: int, data: dict
    ) -> bool:
        """
        Update an existing address.

        The address must belong to the current user's contact. Only
        whitelisted fields are accepted by the repository layer.
        """
        if not user_id or not address_id or not data:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        target = await self._db._address_repo.get_by_id(address_id)
        if not target or int(target.get("contact_id", 0)) != contact_id:
            return False

        # Convert address_type name → id if present
        if "address_type" in data:
            type_name = data.pop("address_type")
            type_row = None
            try:
                type_row = await self._db._address_type_repo.get_by_name(type_name)
            except Exception:
                pass
            if type_row:
                data["address_type_id"] = int(type_row["address_type_id"])

        try:
            return await self._db._address_repo.update(address_id, **data)
        except Exception as exc:
            self._log(f"update_address failed: {exc}", level="ERROR")
            return False

    async def remove_address(self, user_id: int, address_id: int) -> bool:
        """
        Remove an address.

        No restrictions: the user may remove every address they own.
        Returns True on success, False on any failure.
        """
        if not user_id or not address_id:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        target = await self._db._address_repo.get_by_id(address_id)
        if not target or int(target.get("contact_id", 0)) != contact_id:
            return False

        try:
            return await self._db._address_repo.delete(address_id)
        except Exception as exc:
            self._log(f"remove_address failed: {exc}", level="ERROR")
            return False

    # ============================================================
    # Banking — banks lookup
    # ============================================================
    async def list_banks(self) -> list[dict]:
        """Return all enabled banks for the selector."""
        try:
            return await self._db._bank_repo.list_enabled()
        except Exception as exc:
            self._log(f"list_banks failed: {exc}", level="ERROR")
            return []

    async def list_address_types(self) -> list[dict]:
        """Return all enabled address types for the selector."""
        try:
            return await self._db._address_type_repo.list_enabled()
        except Exception as exc:
            self._log(f"list_address_types failed: {exc}", level="ERROR")
            return []

    async def list_phone_types(self) -> list[dict]:
        """Return all enabled phone types for the selector."""
        try:
            return await self._db._phone_type_repo.list_enabled()
        except Exception as exc:
            self._log(f"list_phone_types failed: {exc}", level="ERROR")
            return []

    # ============================================================
    # Banking — accounts
    # ============================================================
    async def list_bank_accounts(self, user_id: int) -> list[dict]:
        """
        Return all bank accounts for the user's contact, each enriched
        with the bank name and its list of cards.
        """
        if not user_id:
            return []

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return []

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return []

        try:
            accounts = await self._db._bank_account_repo.list_by_contact(contact_id)
        except Exception as exc:
            self._log(f"list_bank_accounts failed: {exc}", level="ERROR")
            return []

        # Enrich each account with bank_name + cards
        for acc in accounts:
            bank = None
            try:
                bank = await self._db._bank_repo.get_by_id(acc.get("bank_id"))
            except Exception:
                pass
            acc["bank_name"] = (bank or {}).get("bank_name") or "Unknown bank"

            try:
                acc["cards"] = await self._db._bank_card_repo.list_by_account(
                    acc["bank_account_id"]
                )
            except Exception:
                acc["cards"] = []

        return accounts

    async def add_bank_account(
        self,
        user_id: int,
        bank_id: int,
        account_number: str,
        account_name: str,
        iban: Optional[str] = None,
    ) -> bool:
        if not user_id or not bank_id or not account_number or not account_name:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        # Verify the bank exists
        bank = await self._db._bank_repo.get_by_id(bank_id)
        if not bank:
            return False

        try:
            new_id = await self._db._bank_account_repo.create(
                contact_id=contact_id,
                bank_id=bank_id,
                account_number=account_number,
                account_name=account_name,
                iban=iban,
            )
            return bool(new_id)
        except Exception as exc:
            self._log(f"add_bank_account failed: {exc}", level="ERROR")
            return False

    async def update_bank_account(
        self, user_id: int, account_id: int, data: dict
    ) -> bool:
        if not user_id or not account_id or not data:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        target = await self._db._bank_account_repo.get_by_id(account_id)
        if not target or int(target.get("contact_id", 0)) != contact_id:
            return False

        # If bank_id is being changed, verify the new bank exists
        new_bank_id = data.get("bank_id")
        if new_bank_id:
            bank = await self._db._bank_repo.get_by_id(new_bank_id)
            if not bank:
                return False

        try:
            return await self._db._bank_account_repo.update(account_id, **data)
        except Exception as exc:
            self._log(f"update_bank_account failed: {exc}", level="ERROR")
            return False

    async def remove_bank_account(self, user_id: int, account_id: int) -> tuple:
        """
        Remove a bank account.

        Rules:
            • Cannot remove an account that still has cards.
              The user must delete the cards first.

        Returns
        -------
        tuple (ok: bool, reason: str)
            reason is one of: "ok", "has_cards", "not_found"
        """
        if not user_id or not account_id:
            return False, "not_found"

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False, "not_found"

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False, "not_found"

        target = await self._db._bank_account_repo.get_by_id(account_id)
        if not target or int(target.get("contact_id", 0)) != contact_id:
            return False, "not_found"

        # Refuse to remove if any cards still reference this account
        try:
            cards = await self._db._bank_card_repo.list_by_account(account_id)
        except Exception:
            cards = []
        if cards:
            return False, "has_cards"

        try:
            ok = await self._db._bank_account_repo.delete(account_id)
            return (ok, "ok" if ok else "not_found")
        except Exception as exc:
            self._log(f"remove_bank_account failed: {exc}", level="ERROR")
            return False, "not_found"

    # ============================================================
    # Banking — cards
    # ============================================================
    async def add_bank_card(
        self,
        user_id: int,
        account_id: int,
        card_number: str,
        card_holder_name: str,
        expiry_date: Optional[str] = None,
    ) -> bool:
        if not user_id or not account_id or not card_number or not card_holder_name:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        # Verify the account belongs to this contact
        account = await self._db._bank_account_repo.get_by_id(account_id)
        if not account or int(account.get("contact_id", 0)) != contact_id:
            return False

        try:
            new_id = await self._db._bank_card_repo.create(
                bank_account_id=account_id,
                card_number=card_number,
                card_holder_name=card_holder_name,
                expiry_date=expiry_date,
            )
            return bool(new_id)
        except Exception as exc:
            self._log(f"add_bank_card failed: {exc}", level="ERROR")
            return False

    async def update_bank_card(
        self, user_id: int, card_id: int, data: dict
    ) -> bool:
        if not user_id or not card_id or not data:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        card = await self._db._bank_card_repo.get_by_id(card_id)
        if not card:
            return False

        # Card must belong to an account of this contact
        account = await self._db._bank_account_repo.get_by_id(
            card.get("bank_account_id")
        )
        if not account or int(account.get("contact_id", 0)) != contact_id:
            return False

        try:
            return await self._db._bank_card_repo.update(card_id, **data)
        except Exception as exc:
            self._log(f"update_bank_card failed: {exc}", level="ERROR")
            return False

    async def remove_bank_card(self, user_id: int, card_id: int) -> bool:
        if not user_id or not card_id:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        card = await self._db._bank_card_repo.get_by_id(card_id)
        if not card:
            return False

        account = await self._db._bank_account_repo.get_by_id(
            card.get("bank_account_id")
        )
        if not account or int(account.get("contact_id", 0)) != contact_id:
            return False

        try:
            return await self._db._bank_card_repo.delete(card_id)
        except Exception as exc:
            self._log(f"remove_bank_card failed: {exc}", level="ERROR")
            return False

    # ============================================================
    # Banking — enable/disable
    # ============================================================
    async def set_bank_account_enabled(
        self,
        user_id: int,
        account_id: int,
        enabled: bool,
        cascade_cards: bool = False,
    ) -> bool:
        """
        Enable or disable a bank account.

        Parameters
        ----------
        cascade_cards : bool
            If True, also set the same enabled state on every card
            belonging to this account.

        Returns True on success.
        """
        if not user_id or not account_id:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        account = await self._db._bank_account_repo.get_by_id(account_id)
        if not account or int(account.get("contact_id", 0)) != contact_id:
            return False

        try:
            ok = await self._db._bank_account_repo.set_enabled(
                account_id, enabled
            )
            if not ok:
                return False

            if cascade_cards:
                await self._db._bank_card_repo.set_enabled_by_account(
                    account_id, enabled
                )

            return True
        except Exception as exc:
            self._log(f"set_bank_account_enabled failed: {exc}", level="ERROR")
            return False

    async def set_bank_card_enabled(
        self,
        user_id: int,
        card_id: int,
        enabled: bool,
    ) -> bool:
        """Enable or disable a single bank card."""
        if not user_id or not card_id:
            return False

        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            return False

        people = await self._db._people_repo.get_by_id(user.people_id)
        contact_id = int(people["contact_id"]) if people else 0
        if not contact_id:
            return False

        card = await self._db._bank_card_repo.get_by_id(card_id)
        if not card:
            return False

        account = await self._db._bank_account_repo.get_by_id(
            card.get("bank_account_id")
        )
        if not account or int(account.get("contact_id", 0)) != contact_id:
            return False

        try:
            return await self._db._bank_card_repo.set_enabled(card_id, enabled)
        except Exception as exc:
            self._log(f"set_bank_card_enabled failed: {exc}", level="ERROR")
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
