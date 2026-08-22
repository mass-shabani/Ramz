"""
Route Manager Module - Pure infrastructure for route management.
Provides helper services for other modules to register routes and delegates error handling to message_view.
"""
from massir.core.interfaces import IModule, ModuleContext
from .router import GlobalRouter


class RouteManagerModule(IModule):
    """
    Route manager module.
    Provides route_manager service for centralized route handling.
    """

    def __init__(self):
        self.logger = None
        self.http_api = None
        self.message_service = None
        self.global_router = None

    async def load(self, context: ModuleContext):
        """Get services from context."""
        self.logger = context.services.get("core_logger")
        self.http_api = context.services.get("http_api")
        self.message_service = context.services.get("message_service")
        
        if self.logger:
            self.logger.log("RouteManager module loaded", tag="routes")

    async def start(self, context: ModuleContext):
        """Initialize global router and register error handlers."""
        if not self.http_api or not self.message_service:
            if self.logger:
                self.logger.log("http_api or message_service not available, cannot start route_manager", 
                              level="ERROR", tag="routes")
            return

        # Initialize the global router with required services
        self.global_router = GlobalRouter(
            http_api=self.http_api,
            message_service=self.message_service,
            logger=self.logger
        )

        # Register global error handlers (delegates to message_view)
        self.global_router.register_global_endpoints()

        # Expose the router as a service for other modules
        context.services.set("route_manager", self.global_router)
        
        if self.logger:
            self.logger.log("RouteManager module started successfully", tag="routes")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("RouteManager module stopped", tag="routes")