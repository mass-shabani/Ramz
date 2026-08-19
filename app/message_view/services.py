"""
Message Service - Handles rendering of message templates.
"""
from typing import Any, Dict


class MessageService:
    """
    Provides methods to render standardized message views (errors, alerts, etc.).
    Used by route_manager for error handling and by other modules for notifications.
    """
    
    def __init__(self, template_service: Any, logger: Any):
        self.template_service = template_service
        self.logger = logger

    async def render_message(self, status_code: int, title: str, message: str, message_type: str = "info") -> str:
        """
        Render a message template with the given context.
        
        Args:
            status_code: HTTP status code (e.g., 404, 500)
            title: Title of the message
            message: Detailed message content
            message_type: Type of message (error, warning, success, info)
            
        Returns:
            Rendered HTML string
        """
        context = {
            "status_code": status_code,
            "title": title,
            "message": message,
            "type": message_type,
            "module_name": "message_view"
        }
        
        try:
            return await self.template_service.render("message.html", context)
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error rendering message template: {e}", level="ERROR", tag="messages")
            return f"<h1>{status_code} - {title}</h1><p>{message}</p>"