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
    name = "template_service"
    provides = ["template_service", "menu_manager", "asset_service"]
    requires = ["core_logger", "http_api"]

    def __init__(self):
        self.logger = None
        self.http_api = None
        self.template_manager = None
        self.menu_manager = None
        self.asset_service = None

    async def load(self, context: ModuleContext):
        """Get services from context."""
        self.logger = context.services.get("core_logger")
        self.http_api = context.services.get("http_api")
        
        if self.logger:
            self.logger.log("TemplateService module loaded", tag="template")

    async def start(self, context: ModuleContext):
        """Initialize managers, mount static files, and register routes."""
        if not self.http_api:
            if self.logger:
                self.logger.log("http_api not available, cannot start template_service", 
                              level="ERROR", tag="template")
            return

        module_dir = Path(__file__).parent.resolve()
        templates_dir = module_dir / "templates"
        static_dir = module_dir / "static"

        self.template_manager = TemplateManager(templates_dir=templates_dir, logger=self.logger)
        self.menu_manager = MenuManager(self.logger)
        self.asset_service = AssetService(self.logger)

        # 1. Mount global static files directory
        await self._mount_static_files(static_dir, url_prefix="/static")

        # 2. Register the favicon route
        self._register_favicon_route()

        # 3. Register services for other modules
        context.services.set("template_service", self.template_manager)
        context.services.set("menu_manager", self.menu_manager)
        context.services.set("asset_service", self.asset_service)

        if self.logger:
            self.logger.log("TemplateService module started successfully", tag="template")

    async def _mount_static_files(self, static_dir: Path, url_prefix: str):
        """Mount the static files directory to the HTTP application."""
        try:
            # Local import to avoid top-level dependency on FastAPI
            from fastapi.staticfiles import StaticFiles
            
            app = self._get_fastapi_app()
            if app and static_dir.exists():
                app.mount(url_prefix, StaticFiles(directory=str(static_dir)), name="global_static")
                if self.logger:
                    self.logger.log(f"Static files mounted at {url_prefix}", tag="template")
        except ImportError as e:
            if self.logger:
                self.logger.log(f"Static file mounting failed (missing dependency): {e}", 
                              level="WARNING", tag="template")
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error mounting static files: {e}", level="ERROR", tag="template")

    def _register_favicon_route(self):
        """Register the /favicon.ico route."""
        if not self.http_api:
            return

        @self.http_api.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            favicon_url = self.asset_service.get_url("favicon")
            # Use http_api's RedirectResponse instead of direct FastAPI import
            return self.http_api.RedirectResponse(url=favicon_url, status_code=302)

    def _get_fastapi_app(self):
        """Retrieve the underlying application instance."""
        if hasattr(self.http_api, 'get_app'):
            return self.http_api.get_app()
        elif hasattr(self.http_api, 'app'):
            return self.http_api.app
        return None

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("TemplateService module stopped", tag="template")