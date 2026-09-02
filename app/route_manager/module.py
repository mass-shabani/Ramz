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

    async def start(self, context: ModuleContext):
        """Get services, initialize global router, and register error handlers."""
        logger = context.services.get("core_logger")
        http_api = context.services.get("http_api")
        message_service = context.services.get("message_service")
        
        if logger:
            logger.log("RouteManager module started", tag="routes")

        if not http_api or not message_service:
            if logger:
                logger.log("http_api or message_service not available, cannot start route_manager", 
                              level="ERROR", tag="routes")
            return

        global_router = GlobalRouter(
            http_api=http_api,
            message_service=message_service,
            logger=logger
        )

        global_router.register_global_endpoints()

        context.services.set("route_manager", global_router)
        
        if logger:
            logger.log("RouteManager module started successfully", tag="routes")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        logger = context.services.get("core_logger")
        if logger:
            logger.log("RouteManager module stopped", tag="routes")
