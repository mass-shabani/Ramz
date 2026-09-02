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

    async def start(self, context: ModuleContext):
        """Get services, register template directory and routes."""
        logger = context.services.get("core_logger")
        http_api = context.services.get("http_api")
        template_service = context.services.get("template_service")
        
        if logger:
            logger.log("Home module started", tag="home")

        if not http_api or not template_service:
            if logger:
                logger.log("Required services not available, cannot start home module", 
                              level="ERROR", tag="home")
            return

        from pathlib import Path
        templates_dir = str(Path(__file__).parent / "templates")
        template_service.register_template_directory(templates_dir, "home")
        
        register_routes(http_api, template_service, logger)
        
        if logger:
            logger.log("Home module started successfully", tag="home")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        logger = context.services.get("core_logger")
        if logger:
            logger.log("Home module stopped", tag="home")
