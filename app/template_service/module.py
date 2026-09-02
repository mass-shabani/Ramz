"""
Template Service Module - Central hub for Jinja2 templating, theme management,
static asset mounting, and menu registry.
"""
from pathlib import Path
from massir.core.interfaces import IModule, ModuleContext
from .manager import TemplateManager, MenuManager, AssetService


class TemplateServiceModule(IModule):
    """
    Template service module.
    Provides template_service, menu_manager, and asset_service to other modules.
    """

    async def start(self, context: ModuleContext):
        """Get services, initialize managers, register services, mount static files, and register routes."""
        logger = context.services.get("core_logger")
        http_api = context.services.get("http_api")
        
        if logger:
            logger.log("TemplateService module started", tag="template")

        module_dir = Path(__file__).parent.resolve()
        templates_dir = module_dir / "templates"
        
        template_manager = TemplateManager(templates_dir=templates_dir, logger=logger)
        menu_manager = MenuManager(logger)
        asset_service = AssetService(logger)
        
        context.services.set("template_service", template_manager)
        context.services.set("menu_manager", menu_manager)
        context.services.set("asset_service", asset_service)
        
        if not http_api:
            if logger:
                logger.log("http_api not available, cannot start template_service", 
                              level="ERROR", tag="template")
            return

        static_dir = module_dir / "static"

        try:
            if hasattr(http_api, 'app') and hasattr(http_api, 'StaticFiles'):
                http_api.app.mount(
                    "/static", 
                    http_api.StaticFiles(directory=str(static_dir)), 
                )
                if logger:
                    logger.log("Static files mounted at /static", tag="template")
            else:
                if logger:
                    logger.log("http_api does not expose app or StaticFiles for mounting", 
                                  level="WARNING", tag="template")
        except Exception as e:
            if logger:
                logger.log(f"Error mounting static files: {e}", level="ERROR", tag="template")

        @http_api.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            favicon_url = asset_service.get_url("favicon")
            return http_api.RedirectResponse(url=favicon_url, status_code=302)
        
        if logger:
            logger.log("TemplateService module started successfully", tag="template")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        logger = context.services.get("core_logger")
        if logger:
            logger.log("TemplateService module stopped", tag="template")
