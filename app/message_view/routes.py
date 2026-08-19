"""
Message Routes - Defines HTTP endpoints for displaying messages.
"""
from typing import Any


def register_routes(http_api: Any, message_service: Any, logger: Any):
    """
    Register message view routes with the HTTP API.
    """
    
    @http_api.get("/messages/view", include_in_schema=False, response_class=http_api.HTMLResponse)
    async def view_message(type: str = "info", code: int = 200, title: str = "Message", message: str = ""):
        """
        General endpoint to display a message page.
        """
        try:
            html_content = await message_service.render_message(
                status_code=code,
                title=title,
                message=message,
                message_type=type
            )
            # Use http_api's HTMLResponse
            return http_api.HTMLResponse(content=html_content, status_code=code)
            
        except Exception as e:
            if logger:
                logger.log(f"Error in view_message route: {e}", level="ERROR", tag="messages")
            return http_api.HTMLResponse(content=f"<h1>Error</h1><p>{e}</p>", status_code=500)