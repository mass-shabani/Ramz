"""
DB Manager Module

Provides `app_db_service` — the central database access facade for the
Ramz application.

The service is implemented by DbManagerService (in db_manager_service.py)
and wraps the framework's `database_service`.
"""
from massir.core.interfaces import IModule, ModuleContext


class DbManagerModule(IModule):
    """
    Database manager module.

    Responsibilities:
        • Obtain `database_service` from the framework.
        • Register `app_db_service` (the DbManagerService facade).
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

        try:
            from .db_manager_service import DbManagerService
            service = DbManagerService(database_service, logger)
            context.services.set("app_db_service", service)
            if logger:
                logger.log(
                    "app_db_service registered (DbManagerService)",
                    tag="database",
                )
        except Exception as exc:
            if logger:
                logger.log(
                    f"Failed to register app_db_service: {exc}",
                    level="ERROR",
                    tag="database",
                )
            return

        if logger:
            logger.log("DB Manager module started", tag="database")

    async def stop(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("DB Manager module stopped", tag="database")
