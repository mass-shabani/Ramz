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

    def __init__(self):
        self.logger = None
        self.http_api = None
        self.template_manager = None
        self.menu_manager = None
        self.asset_service = None

    async def load(self, context: ModuleContext):
        """Get services, initialize managers, and REGISTER SERVICES IMMEDIATELY."""
        self.logger = context.services.get("core_logger")
        self.http_api = context.services.get("http_api")
        
        if self.logger:
            self.logger.log("TemplateService module loaded", tag="template")

        # Initialize managers in LOAD phase so they are available for other modules
        module_dir = Path(__file__).parent.resolve()
        templates_dir = module_dir / "templates"
        
        self.template_manager = TemplateManager(templates_dir=templates_dir, logger=self.logger)
        self.menu_manager = MenuManager(self.logger)
        self.asset_service = AssetService(self.logger)
        
        # CRITICAL: Register services in LOAD phase to satisfy dependency resolution
        context.services.set("template_service", self.template_manager)
        context.services.set("menu_manager", self.menu_manager)
        context.services.set("asset_service", self.asset_service)

    async def start(self, context: ModuleContext):
        """Mount static files and register routes (requires http_api to be fully ready)."""
        if not self.http_api:
            if self.logger:
                self.logger.log("http_api not available, cannot start template_service", 
                              level="ERROR", tag="template")
            return

        module_dir = Path(__file__).parent.resolve()
        static_dir = module_dir / "static"

        # 1. Mount global static files directory using http_api abstraction
        await self._mount_static_files(static_dir, url_prefix="/static")

        # 2. Register the favicon route using http_api abstraction
        self._register_favicon_route()

        if self.logger:
            self.logger.log("TemplateService module started successfully", tag="template")

    async def _mount_static_files(self, static_dir: Path, url_prefix: str):
        """
        Mount the static files directory to the HTTP application via http_api service.
        NO direct FastAPI imports (like 'from fastapi.staticfiles import StaticFiles') are used.
        """
        try:
            # Use the abstractions explicitly exposed by network_fastapi's HTTPAPI class
            if hasattr(self.http_api, 'app') and hasattr(self.http_api, 'StaticFiles'):
                self.http_api.app.mount(
                    url_prefix, 
                    self.http_api.StaticFiles(directory=str(static_dir)), 
                )
                if self.logger:
                    self.logger.log(f"Static files mounted at {url_prefix}", tag="template")
            else:
                if self.logger:
                    self.logger.log("http_api does not expose app or StaticFiles for mounting", 
                                  level="WARNING", tag="template")
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error mounting static files: {e}", level="ERROR", tag="template")

    def _register_favicon_route(self):
        """Register the /favicon.ico route using http_api service."""
        if not self.http_api:
            return

        # Use http_api's route decorator and its abstracted RedirectResponse
        @self.http_api.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            favicon_url = self.asset_service.get_url("favicon")
            return self.http_api.RedirectResponse(url=favicon_url, status_code=302)

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("TemplateService module stopped", tag="template")