"""
Home Routes - Defines HTTP endpoints for the home page.
"""
from typing import Any


def register_routes(http_api: Any, template_service: Any, message_service: Any, logger: Any):
    """
    Register home page routes with the HTTP API.
    """
    
    @http_api.get("/", response_class=http_api.HTMLResponse)
    async def home_page(request: http_api.Request):
        """Render the home page."""
        try:
            context = {
                "title": "Ramz — AI Crypto Intelligence",
                "login_url": "/login",
                "module_name": "home",
                "request": request
            }
            
            html_content = await template_service.render("index.html", context)
            # Use http_api's HTMLResponse
            return http_api.HTMLResponse(content=html_content)
            
        except Exception as e:
            if logger:
                logger.log(f"Error rendering home page: {e}", level="ERROR", tag="home")
            if message_service:
                error_html = await message_service.render_message(
                    status_code=500,
                    title="Internal Server Error",
                    message="Failed to load home page. Please try again later.",
                    message_type="error"
                )
                return http_api.HTMLResponse(content=error_html, status_code=500)
            return http_api.HTMLResponse(
                content="<h1>500 - Internal Server Error</h1><p>Failed to load home page.</p>",
                status_code=500
            )