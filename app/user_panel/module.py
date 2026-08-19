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
    name = "user_panel"
    provides = ["panel_service"]
    requires = ["core_logger", "http_api", "template_service", "menu_manager", "asset_service"]

    def __init__(self):
        self.logger = None
        self.http_api = None
        self.template_service = None
        self.menu_manager = None
        self.asset_service = None
        self.panel_service = None

    async def load(self, context: ModuleContext):
        """Get services from context."""
        self.logger = context.services.get("core_logger")
        self.http_api = context.services.get("http_api")
        self.template_service = context.services.get("template_service")
        self.menu_manager = context.services.get("menu_manager")
        self.asset_service = context.services.get("asset_service")
        
        if self.logger:
            self.logger.log("UserPanel module loaded", tag="panel")

    async def start(self, context: ModuleContext):
        """Initialize panel service, register templates, assets, and routes."""
        if not self.http_api or not self.template_service or not self.menu_manager:
            if self.logger:
                self.logger.log("Required services not available, cannot start user_panel", 
                              level="ERROR", tag="panel")
            return

        # 1. Register template directory
        templates_dir = str(Path(__file__).parent / "templates")
        self.template_service.register_template_directory(templates_dir, "user_panel")

        # 2. Register module assets (Lit component for sidebar)
        self.template_service.register_module_assets(
            "user_panel",
            js_files=["/static/js/sidebar.js"]
        )

        # 3. Initialize panel service
        self.panel_service = PanelService(self.template_service, self.menu_manager, self.logger)
        context.services.set("panel_service", self.panel_service)

        # 4. Register default sidebar items for this module
        self.menu_manager.register_menu_item(
            menu_id="sidebar",
            item_id="panel_dashboard",
            label="داشبورد",
            url="/panel",
            icon="🏠",
            tooltip="صفحه اصلی پنل",
            order=10
        )

        # 5. Register routes
        register_routes(self.http_api, self.panel_service, self.logger)
        
        if self.logger:
            self.logger.log("UserPanel module started successfully", tag="panel")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("UserPanel module stopped", tag="panel")