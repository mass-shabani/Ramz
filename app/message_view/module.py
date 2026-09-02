"""
Message View Module - Manages and serves message views (errors, alerts, notifications).
Provides message_service for other modules to render standardized messages.
"""
from pathlib import Path
from massir.core.interfaces import IModule, ModuleContext
from .services import MessageService
from .routes import register_routes


class MessageViewModule(IModule):
    """
    Message view module.
    Provides message_service for rendering messages and registers message routes.
    """

    async def start(self, context: ModuleContext):
        """Get services, initialize service, register template directory and routes."""
        logger = context.services.get("core_logger")
        http_api = context.services.get("http_api")
        template_service = context.services.get("template_service")
        
        if logger:
            logger.log("MessageView module started", tag="messages")

        if template_service:
            message_service = MessageService(template_service, logger)
            context.services.set("message_service", message_service)

        if not http_api or not template_service:
            if logger:
                logger.log("Required services not available, cannot start message_view", 
                              level="ERROR", tag="messages")
            return

        templates_dir = str(Path(__file__).parent / "templates")
        template_service.register_template_directory(templates_dir, "message_view")

        register_routes(http_api, message_service, logger)
        
        if logger:
            logger.log("MessageView module started successfully", tag="messages")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        logger = context.services.get("core_logger")
        if logger:
            logger.log("MessageView module stopped", tag="messages")
