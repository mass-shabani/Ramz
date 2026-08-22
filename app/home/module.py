"""
Home Module - Manages the home page of the application.
Currently displays a login button for user authentication.
"""
from massir.core.interfaces import IModule, ModuleContext
from .routes import register_routes


class HomeModule(IModule):
    """
    Home module that provides the main landing page.
    """

    def __init__(self):
        self.logger = None
        self.http_api = None
        self.template_service = None

    async def load(self, context: ModuleContext):
        """Get services from context."""
        self.logger = context.services.get("core_logger")
        self.http_api = context.services.get("http_api")
        self.template_service = context.services.get("template_service")
        
        if self.logger:
            self.logger.log("Home module loaded", tag="home")

    async def start(self, context: ModuleContext):
        """Register home page routes and template directory."""
        if not self.http_api or not self.template_service:
            if self.logger:
                self.logger.log("Required services not available, cannot start home module", 
                              level="ERROR", tag="home")
            return

        # Register template directory with template_service
        from pathlib import Path
        templates_dir = str(Path(__file__).parent / "templates")
        self.template_service.register_template_directory(templates_dir, "home")
        
        # Register module assets (if any CSS/JS specific to home page)
        # self.template_service.register_module_assets(
        #     "home",
        #     css_files=["/static/css/home.css"],
        #     js_files=["/static/js/home.js"]
        # )
        
        # Register routes
        register_routes(self.http_api, self.template_service, self.logger)
        
        if self.logger:
            self.logger.log("Home module started successfully", tag="home")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("Home module stopped", tag="home")