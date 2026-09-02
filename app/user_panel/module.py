"""
User Panel Module - Manages the user panel layout, sidebar navigation, and dashboard.
Provides panel_service for other modules to render their views inside the panel.
"""
from pathlib import Path
from massir.core.interfaces import IModule, ModuleContext
from .services import PanelService
from .routes import register_routes


class UserPanelModule(IModule):
    """
    User panel module.
    Provides panel_service and registers panel routes.
    """

    async def start(self, context: ModuleContext):
        """Get services, initialize panel service, register templates, assets, menu items, and routes."""
        logger = context.services.get("core_logger")
        http_api = context.services.get("http_api")
        template_service = context.services.get("template_service")
        menu_manager = context.services.get("menu_manager")
        asset_service = context.services.get("asset_service")
        
        if logger:
            logger.log("UserPanel module started", tag="panel")

        if not http_api or not template_service or not menu_manager:
            if logger:
                logger.log("Required services not available, cannot start user_panel", 
                              level="ERROR", tag="panel")
            return

        panel_service = PanelService(template_service, menu_manager, logger)
        context.services.set("panel_service", panel_service)

        templates_dir = str(Path(__file__).parent / "templates")
        template_service.register_template_directory(templates_dir, "user_panel")

        template_service.register_module_assets(
            "user_panel",
            js_files=["/static/js/sidebar.js"]
        )

        menu_manager.register_menu_item(
            menu_id="sidebar",
            item_id="panel_dashboard",
            label="Dashboard",
            url="/panel",
            icon="🏠",
            tooltip="Panel Home",
            order=10
        )

        register_routes(http_api, panel_service, logger)
        
        if logger:
            logger.log("UserPanel module started successfully", tag="panel")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        logger = context.services.get("core_logger")
        if logger:
            logger.log("UserPanel module stopped", tag="panel")
