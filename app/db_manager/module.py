"""
DB Manager Module

Two services are exposed during the migration to the new architecture:

    • app_db_service      — legacy service (from database.py). Kept for
                            backward compatibility until all callers are
                            migrated to the new service.

    • app_db_service_new  — new service (from db_manager_service.py).
                            Under construction. No caller should use it
                            directly yet.

At the end of the migration (phase 8) the legacy service will be removed
and app_db_service will point to the new implementation.
"""
from massir.core.interfaces import IModule, ModuleContext


class DBManagerModule(IModule):
    """
    Database manager module.

    Responsibilities:
        • Obtain `database_service` from the framework.
        • Register the legacy `app_db_service` (temporary).
        • Register the new `app_db_service_new` (under construction).
        • Log the module startup.
    """

    async def start(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        database_service = context.services.get("database_service")

        if logger:
            logger.log("DB Manager module starting…", tag="database")

        if not database_service:
            if logger:
                logger.log(
                    "database_service is not available — db_manager cannot start",
                    level="ERROR",
                    tag="database",
                )
            return

        # ------------------------------------------------------------
        # Legacy service — kept for backward compatibility
        # ------------------------------------------------------------
        try:
            from .database import AppDatabaseManager
            legacy_service = AppDatabaseManager(database_service, logger)
            context.services.set("app_db_service", legacy_service)
            if logger:
                logger.log(
                    "Legacy app_db_service registered (temporary)",
                    tag="database",
                )
        except Exception as exc:
            if logger:
                logger.log(
                    f"Failed to register legacy app_db_service: {exc}",
                    level="ERROR",
                    tag="database",
                )

        # ------------------------------------------------------------
        # New service — under construction
        # ------------------------------------------------------------
        try:
            from .db_manager_service import DbManagerService
            new_service = DbManagerService(database_service, logger)
            context.services.set("app_db_service_new", new_service)
            if logger:
                logger.log(
                    "New app_db_service_new registered (under construction)",
                    tag="database",
                )
        except Exception as exc:
            if logger:
                logger.log(
                    f"Failed to register app_db_service_new: {exc}",
                    level="ERROR",
                    tag="database",
                )

        if logger:
            logger.log("DB Manager module started", tag="database")

    async def stop(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("DB Manager module stopped", tag="database")
