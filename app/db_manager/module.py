"""
Database Manager Module - Manages application database schema using system database service.
This module defines tables, creates them via database_service, and exposes app_db_service.
"""
from massir.core.interfaces import IModule, ModuleContext
from .database import AppDatabaseManager
from .models import get_app_tables

class DbManagerModule(IModule):
    """
    Database manager module.
    Provides app_db_service for other modules to interact with application database tables.
    """

    async def start(self, context: ModuleContext):
        """Get services, initialize manager, register service, and create tables."""
        logger = context.services.get("core_logger")
        config = context.services.get("core_config")
        database_service = context.services.get("database_service")
        database_types = context.services.get("database_types")
        
        if logger:
            logger.log("DbManager module started", tag="database")

        if database_service:
            db_manager = AppDatabaseManager(database_service, logger)
            context.services.set("app_db_service", db_manager)

            if database_types:
                tables = get_app_tables(database_types)
                
                try:
                    for table_def in tables:
                        await db_manager.create_table(table_def)
                    if logger:
                        logger.log(f"Database tables created/verified successfully ({len(tables)} tables)", tag="database")
                except Exception as e:
                    if logger:
                        logger.log(f"Error creating database tables: {e}", level="ERROR", tag="database")
        else:
            if logger:
                logger.log("Required services not available, cannot start db_manager", 
                              level="ERROR", tag="database")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        logger = context.services.get("core_logger")
        if logger:
            logger.log("DbManager module stopped", tag="database")
