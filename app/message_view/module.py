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
    name = "message_view"
    provides = ["message_service"]
    requires = ["core_logger", "http_api", "template_service"]

    def __init__(self):
        self.logger = None
        self.http_api = None
        self.template_service = None
        self.message_service = None

    async def load(self, context: ModuleContext):
        """Get services from context."""
        self.logger = context.services.get("core_logger")
        self.http_api = context.services.get("http_api")
        self.template_service = context.services.get("template_service")
        
        if self.logger:
            self.logger.log("MessageView module loaded", tag="messages")

        # Initialize service and REGISTER in LOAD phase
        if self.template_service:
            self.message_service = MessageService(self.template_service, self.logger)
            context.services.set("message_service", self.message_service)

    async def start(self, context: ModuleContext):
        """Register template directory and routes."""
        if not self.http_api or not self.template_service:
            if self.logger:
                self.logger.log("Required services not available, cannot start message_view", 
                              level="ERROR", tag="messages")
            return

        # Register template directory
        templates_dir = str(Path(__file__).parent / "templates")
        self.template_service.register_template_directory(templates_dir, "message_view")

        # Register routes
        register_routes(self.http_api, self.message_service, self.logger)
        
        if self.logger:
            self.logger.log("MessageView module started successfully", tag="messages")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("MessageView module stopped", tag="messages")