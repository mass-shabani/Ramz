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
    name = "db_manager"
    provides = ["app_db_service"]
    requires = ["core_logger", "core_config", "database_service"]

    def __init__(self):
        self.logger = None
        self.config = None
        self.database_service = None
        self.database_types = None
        self.db_manager = None

    async def load(self, context: ModuleContext):
        """Get services and types from context."""
        self.logger = context.services.get("core_logger")
        self.config = context.services.get("core_config")
        self.database_service = context.services.get("database_service")
        
        # Fetch database_types dynamically
        self.database_types = context.services.get("database_types")
        
        if self.logger:
            self.logger.log("DbManager module loaded", tag="database")

        # Initialize manager and REGISTER SERVICE in LOAD phase
        if self.database_service:
            self.db_manager = AppDatabaseManager(self.database_service, self.logger)
            context.services.set("app_db_service", self.db_manager)

    async def start(self, context: ModuleContext):
        """Create database tables (requires database_service to be fully initialized)."""
        if not self.db_manager or not self.database_types:
            if self.logger:
                self.logger.log("Required services not available, cannot start db_manager", 
                              level="ERROR", tag="database")
            return

        # Get table definitions for the application
        tables = get_app_tables(self.database_types)
        
        # Create tables if they don't exist
        try:
            for table_def in tables:
                await self.db_manager.create_table(table_def)
            if self.logger:
                self.logger.log(f"Database tables created/verified successfully ({len(tables)} tables)", tag="database")
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error creating database tables: {e}", level="ERROR", tag="database")

        if self.logger:
            self.logger.log("DbManager module started successfully", tag="database")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("DbManager module stopped", tag="database")