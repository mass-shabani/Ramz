"""
User Info Module - Manages user profile display and editing functionalities.
Integrates with the user panel to provide a seamless profile management experience.
"""
from pathlib import Path
from massir.core.interfaces import IModule, ModuleContext
from .services import UserInfoService
from .routes import register_routes


class UserInfoModule(IModule):
    """
    User info module.
    Provides user_info_service and registers profile management routes.
    """

    def __init__(self):
        self.logger = None
        self.http_api = None
        self.template_service = None
        self.menu_manager = None
        self.panel_service = None
        self.app_db_service = None
        self.user_info_service = None

    async def load(self, context: ModuleContext):
        """Get services from context."""
        self.logger = context.services.get("core_logger")
        self.http_api = context.services.get("http_api")
        self.template_service = context.services.get("template_service")
        self.menu_manager = context.services.get("menu_manager")
        self.panel_service = context.services.get("panel_service")
        self.app_db_service = context.services.get("app_db_service")
        
        if self.logger:
            self.logger.log("UserInfo module loaded", tag="user_info")

    async def start(self, context: ModuleContext):
        """Initialize service, register templates, menu items, and routes."""
        if not all([self.http_api, self.panel_service, self.app_db_service, self.menu_manager]):
            if self.logger:
                self.logger.log("Required services not available, cannot start user_info", 
                              level="ERROR", tag="user_info")
            return

        # 1. Initialize service
        self.user_info_service = UserInfoService(self.app_db_service, self.logger)
        context.services.set("user_info_service", self.user_info_service)

        # 2. Register template directory
        templates_dir = str(Path(__file__).parent / "templates")
        self.template_service.register_template_directory(templates_dir, "user_info")

        # 3. Register sidebar menu item
        self.menu_manager.register_menu_item(
            menu_id="sidebar",
            item_id="user_info_profile",
            label="User Information",
            url="/panel/profile",
            icon="👤",
            tooltip="View and edit account information",
            order=20
        )

        # 4. Register routes
        register_routes(
            self.http_api, 
            self.panel_service, 
            self.user_info_service, 
            self.logger
        )
        
        if self.logger:
            self.logger.log("UserInfo module started successfully", tag="user_info")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("UserInfo module stopped", tag="user_info")