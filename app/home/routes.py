"""
Home Routes - Defines HTTP endpoints for the home page.
"""
from typing import Any


def register_routes(http_api: Any, template_service: Any, logger: Any):
    """
    Register home page routes with the HTTP API.
    """
    
    @http_api.get("/", response_class=http_api.HTMLResponse)
    async def home_page():
        """Render the home page."""
        try:
            context = {
                "title": "Home - Crypto Services",
                "page_title": "Welcome to Crypto Services",
                "page_subtitle": "Your gateway to cryptocurrency management",
                "login_url": "/login",
                "module_name": "home"
            }
            
            html_content = await template_service.render("index.html", context)
            # Use http_api's HTMLResponse
            return http_api.HTMLResponse(content=html_content)
            
        except Exception as e:
            if logger:
                logger.log(f"Error rendering home page: {e}", level="ERROR", tag="home")
            return http_api.HTMLResponse(
                content="<h1>500 - Internal Server Error</h1><p>Failed to load home page.</p>",
                status_code=500
            )