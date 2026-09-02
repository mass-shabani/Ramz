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

    async def start(self, context: ModuleContext):
        """Get services, initialize service, register templates, menu items, and routes."""
        logger = context.services.get("core_logger")
        http_api = context.services.get("http_api")
        template_service = context.services.get("template_service")
        menu_manager = context.services.get("menu_manager")
        panel_service = context.services.get("panel_service")
        app_db_service = context.services.get("app_db_service")
        
        if logger:
            logger.log("UserInfo module started", tag="user_info")

        if not all([http_api, panel_service, app_db_service, menu_manager]):
            if logger:
                logger.log("Required services not available, cannot start user_info", 
                              level="ERROR", tag="user_info")
            return

        user_info_service = UserInfoService(app_db_service, logger)
        context.services.set("user_info_service", user_info_service)

        templates_dir = str(Path(__file__).parent / "templates")
        template_service.register_template_directory(templates_dir, "user_info")

        menu_manager.register_menu_item(
            menu_id="sidebar",
            item_id="user_info_profile",
            label="User Information",
            url="/panel/profile",
            icon="👤",
            tooltip="View and edit account information",
            order=20
        )

        register_routes(
            http_api, 
            panel_service, 
            user_info_service, 
            logger
        )
        
        if logger:
            logger.log("UserInfo module started successfully", tag="user_info")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        logger = context.services.get("core_logger")
        if logger:
            logger.log("UserInfo module stopped", tag="user_info")
