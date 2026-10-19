"""
Signup workflow.

Creates all the records needed for a new user account in a single
atomic operation:

    contact → people → email (optional) → phone (optional) → user

If any step fails, the transaction is rolled back and no partial state
remains in the database.

Design notes
------------
• Pre-checks (username uniqueness, email uniqueness) run BEFORE the
  transaction to fail fast and avoid holding a lock unnecessarily.

• The password is hashed BEFORE the transaction for the same reason.

• Activity logging (signup) happens AFTER the transaction succeeds,
  because it is best-effort and must never roll back a successful
  account creation.
"""
from typing import Optional

from ..models.signup import SignupData
from ..models.user import User
from ..security.password import hash_password


class SignupError(Exception):
    """
    Raised when signup cannot proceed.

    The `code` attribute indicates the reason:
        • "username_exists"
        • "email_exists"
        • "role_not_found"
        • "internal_error"
    """
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


class SignupWorkflow:

    DEFAULT_ROLE = "user"

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _log(self, message, level="INFO"):
        if self._logger:
            try:
                self._logger.log(message, level=level, tag="database")
            except Exception:
                pass

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------
    async def create_account(self, data: SignupData) -> Optional[User]:
        """
        Create a new user account.

        Parameters
        ----------
        data : SignupData

        Returns
        -------
        User or None
            The fully populated User object on success.
            Returns None on failure — inspect the raised SignupError
            for the reason.

        Raises
        ------
        SignupError
            When signup cannot proceed (see SignupError.code).
        """
        # -------- 1. Pre-checks (fail fast, before transaction) --------
        if not data.username or not data.password:
            raise SignupError("internal_error", "username and password required")
        if not data.first_name or not data.last_name:
            raise SignupError("internal_error", "first_name and last_name required")

        existing = await self._db._user_repo.get_by_username(data.username)
        if existing:
            raise SignupError("username_exists")

        if data.email:
            existing_email = await self._db._email_repo.get_by_address(data.email)
            if existing_email:
                raise SignupError("email_exists")

        # -------- 2. Resolve role --------
        role_name = data.role_name or self.DEFAULT_ROLE
        role = await self._db._role_repo.get_by_name(role_name)
        if not role:
            raise SignupError("role_not_found", f"role '{role_name}' not found")
        role_id = role["role_id"]

        # -------- 3. Hash password (outside transaction) --------
        password_hash = hash_password(data.password)

        # -------- 4. Create rows inside a transaction --------
        contact_id: Optional[int] = None
        people_id:  Optional[int] = None
        email_id:   Optional[int] = None
        phone_id:   Optional[int] = None
        user_id:    Optional[int] = None

        try:
            conn = self._db.connection()
            async with conn.transaction():
                # 4.1 — contact hub
                contact_id = await self._db._contact_repo.create()
                if not contact_id:
                    raise SignupError("internal_error", "failed to create contact")

                # 4.2 — people
                people_id = await self._db._people_repo.create(
                    contact_id=contact_id,
                    first_name=data.first_name,
                    last_name=data.last_name,
                    national_code=data.national_code,
                    birth_date=data.birth_date,
                    gender=data.gender,
                )
                if not people_id:
                    raise SignupError("internal_error", "failed to create people")

                # 4.3 — email (optional)
                if data.email:
                    email_id = await self._db._email_repo.create(
                        contact_id=contact_id,
                        email_address=data.email,
                        is_verified=False,
                    )
                    if not email_id:
                        raise SignupError("internal_error", "failed to create email")

                # 4.4 — phone (optional)
                if data.phone:
                    # Resolve type name "mobile" → phone_type_id
                    phone_type_id = 1   # fallback
                    try:
                        type_row = await self._db._phone_type_repo.get_by_name("mobile")
                        if type_row:
                            phone_type_id = int(type_row["phone_type_id"])
                        else:
                            types = await self._db._phone_type_repo.list_enabled()
                            if types:
                                phone_type_id = int(types[0]["phone_type_id"])
                    except Exception:
                        pass

                    phone_id = await self._db._phone_repo.create(
                        contact_id=contact_id,
                        phone_number=data.phone,
                        phone_type_id=phone_type_id,
                        is_verified=False,
                    )
                    if not phone_id:
                        raise SignupError("internal_error", "failed to create phone")

                # 4.5 — user
                user_id = await self._db._user_repo.create(
                    people_id=people_id,
                    role_id=role_id,
                    username=data.username,
                    password_hash=password_hash,
                    email_id=email_id,
                    phone_id=phone_id,
                )
                if not user_id:
                    raise SignupError("internal_error", "failed to create user")

        except SignupError:
            raise
        except Exception as exc:
            self._log(f"Signup transaction failed: {exc}", level="ERROR")
            raise SignupError("internal_error", str(exc))

        # -------- 5. Log the signup activity (best-effort) --------
        try:
            await self._db._activity_repo.log(
                user_id=user_id,
                type_name="signup",
                ip_address=None,
                user_agent=None,
            )
        except Exception as exc:
            self._log(f"Failed to log signup activity: {exc}", level="WARNING")

        # -------- 6. Return the created user --------
        user = await self._db._user_repo.get_by_id(user_id)
        if not user:
            self._log(
                f"Signup succeeded but user {user_id} could not be reloaded",
                level="WARNING",
            )
        return user
