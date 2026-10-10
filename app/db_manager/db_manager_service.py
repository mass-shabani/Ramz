"""
DB Manager Service (Facade)

Central service for all database access in the Ramz application. This
service wraps the framework's `database_service` and exposes high-level
operations that combine multiple tables (authentication, profile,
settings, access control, activity logging).

This service is registered as `app_db_service_new` during the migration
and will become `app_db_service` in phase 8.

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

        self._user_repo = UserRepository(self, logger)
        self._people_repo = PeopleRepository(self, logger)

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
    # Authentication — placeholder
    # ============================================================
    async def authenticate(self, username, password, ip=None, user_agent=None):
        raise NotImplementedError("authenticate — to be implemented in phase 7")

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
    # Sign up — placeholder
    # ============================================================
    async def username_exists(self, username):
        raise NotImplementedError("username_exists — phase 10")

    async def email_exists(self, email):
        raise NotImplementedError("email_exists — phase 10")

    async def create_account(self, data):
        raise NotImplementedError("create_account — phase 10")

    # ============================================================
    # Profile — placeholder
    # ============================================================
    async def get_full_profile(self, user_id):
        raise NotImplementedError("get_full_profile — phase 11")

    async def update_personal_info(self, user_id, data):
        raise NotImplementedError("update_personal_info — phase 11")

    async def update_contact_info(self, user_id, data):
        raise NotImplementedError("update_contact_info — phase 11")

    # ============================================================
    # Settings — placeholder
    # ============================================================
    async def change_password(self, user_id, current, new):
        raise NotImplementedError("change_password — phase 12")

    async def update_email(self, user_id, new_email):
        raise NotImplementedError("update_email — phase 12")

    async def update_phone(self, user_id, new_phone):
        raise NotImplementedError("update_phone — phase 12")

    async def enable_2fa(self, user_id, secret, backup_codes):
        raise NotImplementedError("enable_2fa — phase 12")

    async def disable_2fa(self, user_id):
        raise NotImplementedError("disable_2fa — phase 12")

    # ============================================================
    # Access Control — placeholder
    # ============================================================
    async def has_access(self, user_id, form_name, required_condition=None):
        raise NotImplementedError("has_access — phase 6")

    async def get_accessible_forms(self, user_id):
        raise NotImplementedError("get_accessible_forms — phase 6")

    async def get_form_condition(self, user_id, form_name):
        raise NotImplementedError("get_form_condition — phase 6")

    async def list_user_roles(self, user_id):
        raise NotImplementedError("list_user_roles — phase 6")

    async def list_role_forms(self, role_id):
        raise NotImplementedError("list_role_forms — phase 6")

    def invalidate_access_cache(self, user_id=None):
        raise NotImplementedError("invalidate_access_cache — phase 5")

    def invalidate_form_cache(self, form_name=None):
        raise NotImplementedError("invalidate_form_cache — phase 5")

    # ============================================================
    # Activity — placeholder
    # ============================================================
    async def log_activity(self, user_id, activity_type, ip=None, user_agent=None):
        raise NotImplementedError("log_activity — phase 13")

    async def get_user_activities(self, user_id, limit=20, offset=0):
        raise NotImplementedError("get_user_activities — phase 13")

    async def get_activity_types(self):
        raise NotImplementedError("get_activity_types — phase 13")
