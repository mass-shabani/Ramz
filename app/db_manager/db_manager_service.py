"""
DB Manager Service (Facade)

Central service for all database access in the Ramz application. This
service wraps the framework's `database_service` and exposes high-level
operations that combine multiple tables (authentication, profile,
settings, access control, activity logging).

This service is registered as `app_db_service`.

Layer structure:
    DbManagerService
        ├── security/     — password hashing, access checking
        ├── models/       — dataclasses for transferring data
        ├── repositories/ — single-table CRUD operations
        └── workflows/    — multi-table business operations

Nothing in this file should be considered final. It is a skeleton to be
filled in during the migration phases.
"""


class DbManagerService:
    """
    High-level database service for the Ramz application.

    Constructor receives the framework's database service and the module
    logger. Both are stored for use by repositories and workflows.
    """

    # Name of the connection declared in app_settings.json
    DEFAULT_CONNECTION = "default"

    def __init__(self, database_service, logger=None):
        self._db = database_service
        self._logger = logger

        # ----------------------------------------------------------
        # Repositories
        # ----------------------------------------------------------
        from .repositories.user_repository import UserRepository
        from .repositories.people_repository import PeopleRepository
        from .repositories.role_repository import RoleRepository
        from .repositories.form_repository import FormRepository
        from .repositories.condition_repository import ConditionRepository
        from .repositories.form_access_repository import FormAccessRepository
        from .repositories.activity_repository import ActivityRepository
        from .repositories.contact_repository import ContactRepository
        from .repositories.email_repository import EmailRepository
        from .repositories.phone_repository import PhoneRepository
        from .repositories.address_repository import AddressRepository
        from .repositories.subscription_repository import SubscriptionRepository
        from .repositories.bank_repository import BankRepository
        from .repositories.bank_account_repository import BankAccountRepository
        from .repositories.bank_card_repository import BankCardRepository

        self._user_repo = UserRepository(self, logger)
        self._people_repo = PeopleRepository(self, logger)
        self._role_repo = RoleRepository(self, logger)
        self._form_repo = FormRepository(self, logger)
        self._condition_repo = ConditionRepository(self, logger)
        self._form_access_repo = FormAccessRepository(self, logger)
        self._activity_repo = ActivityRepository(self, logger)
        self._contact_repo = ContactRepository(self, logger)
        self._email_repo = EmailRepository(self, logger)
        self._phone_repo = PhoneRepository(self, logger)
        self._address_repo = AddressRepository(self, logger)
        self._subscription_repo = SubscriptionRepository(self, logger)
        self._bank_repo = BankRepository(self, logger)
        self._bank_account_repo = BankAccountRepository(self, logger)
        self._bank_card_repo = BankCardRepository(self, logger)

        # ----------------------------------------------------------
        # Security
        # ----------------------------------------------------------
        from .security.access import AccessChecker
        self._access = AccessChecker(self, logger)

        # ----------------------------------------------------------
        # Workflows
        # ----------------------------------------------------------
        from .workflows.login_workflow import LoginWorkflow
        self._login_workflow = LoginWorkflow(self, logger)

        from .workflows.signup_workflow import SignupWorkflow
        self._signup_workflow = SignupWorkflow(self, logger)

        from .workflows.profile_workflow import ProfileWorkflow
        self._profile_workflow = ProfileWorkflow(self, logger)

        from .workflows.settings_workflow import SettingsWorkflow
        self._settings_workflow = SettingsWorkflow(self, logger)

    # ============================================================
    # Internal helpers
    # ============================================================
    def _log(self, message, level="INFO", tag="database"):
        """Safe logging helper — does nothing if no logger is set."""
        if self._logger:
            try:
                self._logger.log(message, level=level, tag=tag)
            except Exception:
                pass

    def connection(self, name: str = None):
        """
        Return a database connection.

        Parameters
        ----------
        name : str, optional
            Connection name as declared in app_settings.json.
            Defaults to DEFAULT_CONNECTION ("default").

        Returns
        -------
        Connection
            A connection object implementing the standard framework API.
        """
        if not self._db:
            raise RuntimeError(
                "database_service is not available — cannot obtain connection"
            )
        return self._db.get_connection(name or self.DEFAULT_CONNECTION)

    # ============================================================
    # Authentication
    # ============================================================
    async def authenticate(self, username, password, ip=None, user_agent=None):
        """
        Attempt to authenticate a user.

        Returns a User object (without password_hash) on success, or
        None on any failure. See LoginWorkflow.login for details.
        """
        return await self._login_workflow.login(
            username=username,
            password=password,
            ip=ip,
            user_agent=user_agent,
        )

    async def authenticate_strict(
        self, username, password, ip=None, user_agent=None
    ):
        """
        Same as authenticate() but raises LoginError on failure.

        Raises
        ------
        app.db_manager.workflows.login_workflow.LoginError
            with codes: invalid_data | invalid_credentials |
            account_disabled
        """
        return await self._login_workflow.login_strict(
            username=username,
            password=password,
            ip=ip,
            user_agent=user_agent,
        )

    async def log_failed_login(self, username, ip=None, user_agent=None):
        """
        Record a failed login attempt for an existing user.

        Returns True if the activity was recorded, False otherwise.
        Safe to call — never raises.
        """
        return await self._login_workflow.log_failed_login(
            username=username,
            ip=ip,
            user_agent=user_agent,
        )

    async def get_user_by_username(self, username):
        """
        Return a fully populated User by username, or None.
        Does not include password_hash.
        """
        return await self._user_repo.get_by_username(username)

    async def get_user_by_id(self, user_id):
        """
        Return a fully populated User by user_id, or None.
        Does not include password_hash.
        """
        return await self._user_repo.get_by_id(user_id)

    async def is_user_enabled(self, user_id):
        """
        Return True if the user is currently enabled.
        Used by access control to invalidate sessions of disabled users.
        """
        return await self._user_repo.is_enabled(user_id)

    # ============================================================
    # Sign up
    # ============================================================
    async def username_exists(self, username):
        """Return True if the username is already taken."""
        if not username:
            return False
        user = await self._user_repo.get_by_username(username)
        return user is not None

    async def email_exists(self, email):
        """Return True if the email is already registered."""
        if not email:
            return False
        row = await self._email_repo.get_by_address(email)
        return row is not None

    async def create_account(self, data):
        """
        Create a new user account.

        Parameters
        ----------
        data : SignupData

        Returns
        -------
        User or None
            The newly created user on success.

        Raises
        ------
        SignupError
            If the account cannot be created. Inspect `error.code` for
            the reason: "username_exists", "email_exists",
            "role_not_found", "internal_error".
        """
        return await self._signup_workflow.create_account(data)

    # ============================================================
    # Profile
    # ============================================================
    async def get_full_profile(self, user_id):
        """
        Return the complete profile of a user as a Profile dataclass,
        or None if the user does not exist.
        """
        return await self._profile_workflow.get_full_profile(user_id)

    async def update_personal_info(self, user_id, data):
        """
        Update personal information (first_name, last_name,
        national_code, birth_date, gender).
        Returns True on success.
        """
        return await self._profile_workflow.update_personal_info(
            user_id, data
        )

    async def update_contact_info(self, user_id, data):
        """
        Update contact information (email, phone, address).
        Returns True on success.
        """
        return await self._profile_workflow.update_contact_info(
            user_id, data
        )

    async def list_contact_channels(self, user_id):
        """Return all emails, phones, and addresses for the user."""
        return await self._profile_workflow.list_contact_channels(user_id)

    async def add_email(self, user_id, email_address):
        return await self._profile_workflow.add_email(user_id, email_address)

    async def remove_email(self, user_id, email_id):
        """Returns (ok: bool, reason: str)."""
        return await self._profile_workflow.remove_email(user_id, email_id)

    async def set_primary_email(self, user_id, email_id):
        return await self._profile_workflow.set_primary_email(user_id, email_id)

    async def add_phone(self, user_id, phone_number, phone_type="mobile"):
        return await self._profile_workflow.add_phone(
            user_id, phone_number, phone_type
        )

    async def remove_phone(self, user_id, phone_id):
        """Returns (ok: bool, reason: str)."""
        return await self._profile_workflow.remove_phone(user_id, phone_id)

    async def set_primary_phone(self, user_id, phone_id):
        return await self._profile_workflow.set_primary_phone(user_id, phone_id)

    async def add_address(self, user_id, address_line1, **kwargs):
        return await self._profile_workflow.add_address(
            user_id, address_line1, **kwargs
        )

    async def update_address(self, user_id, address_id, data):
        return await self._profile_workflow.update_address(
            user_id, address_id, data
        )

    async def remove_address(self, user_id, address_id):
        return await self._profile_workflow.remove_address(user_id, address_id)

    # ============================================================
    # Banking
    # ============================================================
    async def list_banks(self):
        """Return all enabled banks (for the selector)."""
        return await self._profile_workflow.list_banks()

    async def list_bank_accounts(self, user_id):
        """Return all bank accounts + their cards for the user."""
        return await self._profile_workflow.list_bank_accounts(user_id)

    async def add_bank_account(
        self, user_id, bank_id, account_number, account_name, iban=None
    ):
        return await self._profile_workflow.add_bank_account(
            user_id, bank_id, account_number, account_name, iban
        )

    async def update_bank_account(self, user_id, account_id, data):
        return await self._profile_workflow.update_bank_account(
            user_id, account_id, data
        )

    async def remove_bank_account(self, user_id, account_id):
        return await self._profile_workflow.remove_bank_account(
            user_id, account_id
        )

    async def add_bank_card(
        self, user_id, account_id, card_number, card_holder_name,
        expiry_date=None,
    ):
        return await self._profile_workflow.add_bank_card(
            user_id, account_id, card_number, card_holder_name, expiry_date
        )

    async def update_bank_card(self, user_id, card_id, data):
        return await self._profile_workflow.update_bank_card(
            user_id, card_id, data
        )

    async def remove_bank_card(self, user_id, card_id):
        return await self._profile_workflow.remove_bank_card(user_id, card_id)

    async def set_bank_account_enabled(
        self, user_id, account_id, enabled, cascade_cards=False
    ):
        return await self._profile_workflow.set_bank_account_enabled(
            user_id, account_id, enabled, cascade_cards
        )

    async def set_bank_card_enabled(self, user_id, card_id, enabled):
        return await self._profile_workflow.set_bank_card_enabled(
            user_id, card_id, enabled
        )

    # ============================================================
    # Settings
    # ============================================================
    async def change_password(
        self, user_id, current_password, new_password,
        ip=None, user_agent=None,
    ):
        """
        Change the user's password.

        Raises SettingsError with codes:
            invalid_password, weak_password, same_password,
            user_not_found, internal_error
        """
        return await self._settings_workflow.change_password(
            user_id, current_password, new_password, ip, user_agent
        )

    async def update_email(
        self, user_id, new_email, ip=None, user_agent=None
    ):
        """
        Change the primary email.

        Raises SettingsError with codes:
            invalid_data, user_not_found, email_exists, internal_error
        """
        return await self._settings_workflow.update_email(
            user_id, new_email, ip, user_agent
        )

    async def update_phone(
        self, user_id, new_phone, ip=None, user_agent=None
    ):
        """
        Change the primary phone.

        Raises SettingsError with codes:
            invalid_data, user_not_found, phone_exists, internal_error
        """
        return await self._settings_workflow.update_phone(
            user_id, new_phone, ip, user_agent
        )

    async def enable_2fa(
        self, user_id, secret, backup_codes,
        ip=None, user_agent=None,
    ):
        """
        Enable two-factor authentication.

        Raises SettingsError with codes:
            invalid_data, user_not_found, 2fa_already_enabled,
            internal_error
        """
        return await self._settings_workflow.enable_2fa(
            user_id, secret, backup_codes, ip, user_agent
        )

    async def disable_2fa(
        self, user_id, ip=None, user_agent=None
    ):
        """
        Disable two-factor authentication and clear its data.

        Raises SettingsError with codes:
            invalid_data, user_not_found, 2fa_not_enabled, internal_error
        """
        return await self._settings_workflow.disable_2fa(
            user_id, ip, user_agent
        )

    # ============================================================
    # Access Control
    # ============================================================
    async def has_access(self, user_id, form_id, required_condition=None):
        """
        Return True if the user has access to the given form.

        If required_condition is None, any condition counts as access.
        Otherwise the user's condition must match exactly.
        """
        return await self._access.has_access(
            user_id, form_id, required_condition=required_condition
        )

    async def has_public_access(
        self, form_id, required_condition=None
    ):
        """
        Check if a public (unauthenticated) visitor has access to a
        given form.

        Public visitors are treated as members of the 'guest' role.
        If the guest role does not exist or the form is not assigned
        to it, this returns False.

        This is the correct way to make a page conditionally
        available to anonymous users (e.g. /signup can be disabled
        by the admin by revoking guest access to auth.signup.view).
        """
        guest_role_id = await self._get_guest_role_id()
        if guest_role_id is None:
            return False
        return await self._access.has_role_access(
            guest_role_id, form_id, required_condition
        )

    async def get_public_condition(self, form_id):
        """
        Return the condition name the guest role has for the form,
        or None if no access is granted.
        """
        guest_role_id = await self._get_guest_role_id()
        if guest_role_id is None:
            return None
        return await self._access.get_form_condition_by_role(
            guest_role_id, form_id
        )

    async def _get_guest_role_id(self):
        """Return the role_id for the 'guest' role, or None."""
        try:
            role = await self._role_repo.get_by_name("guest")
            if role:
                return int(role["role_id"])
        except Exception as exc:
            self._log(f"Failed to resolve guest role: {exc}", level="ERROR")
        return None

    async def get_accessible_forms(self, user_id):
        """Return the list of form_ids the user can access."""
        return await self._access.get_accessible_forms(user_id)

    async def get_form_condition(self, user_id, form_id):
        """
        Return the condition name the user has for the given form, or
        None. The caller interprets the condition name.
        """
        return await self._access.get_form_condition(user_id, form_id)

    async def get_user_role(self, user_id):
        """Return the user's Role dataclass, or None."""
        return await self._access.get_user_role(user_id)

    async def list_user_roles(self, user_id):
        """
        Return the user's roles as a list.

        The current schema allows exactly one role per user, so the
        list has zero or one element. The list shape is kept for
        future multi-role support.
        """
        role = await self._access.get_user_role(user_id)
        return [role] if role else []

    async def list_role_forms(self, role_id):
        """Return FormAccess objects for the given role."""
        return await self._access.list_role_forms(role_id)

    def invalidate_access_cache(self, user_id=None):
        """Clear user-specific caches (enabled + role)."""
        self._access.invalidate_user(user_id)

    def invalidate_form_cache(self, form_id=None):
        """Clear role-form cache entries for the given form."""
        self._access.invalidate_form(form_id)

    def invalidate_role_cache(self, role_id=None):
        """Clear role-form cache entries for the given role."""
        self._access.invalidate_role(role_id)

    # ============================================================
    # ============================================================
    # Activity
    # ============================================================
    async def log_activity(
        self, user_id, activity_type, ip=None, user_agent=None
    ):
        """
        Record a user activity.

        Never raises. Returns True on success, False on any failure.
        Failures are silently logged.
        """
        return await self._activity_repo.log(
            user_id, activity_type, ip, user_agent
        )

    async def get_user_activities(self, user_id, limit=20, offset=0):
        """
        Return recent activities for the user as Activity dataclasses,
        newest first.
        """
        return await self._activity_repo.get_by_user(
            user_id, limit=limit, offset=offset
        )

    async def count_user_activities(self, user_id):
        """Return the total number of activity rows for the user."""
        return await self._activity_repo.count_by_user(user_id)

    async def get_activity_types(self):
        """
        Return every registered activity type as a list of dicts
        (activity_type_id, type_name, description).
        """
        return await self._activity_repo.list_types()

    def invalidate_activity_type_cache(self):
        """Clear the activity_type id cache."""
        self._activity_repo.invalidate_type_cache()
