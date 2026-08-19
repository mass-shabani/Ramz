"""
Panel Routes - Defines HTTP endpoints for the user panel.
"""
from typing import Any


def register_routes(http_api: Any, panel_service: Any, logger: Any):
    """
    Register user panel routes with the HTTP API.
    """
    
    @http_api.get("/panel", response_class=http_api.HTMLResponse)
    async def panel_dashboard(request: http_api.Request):
        """
        Display the main dashboard page.
        Requires user to be authenticated.
        """
        # Check authentication
        current_user = request.session.get("user") if hasattr(request, "session") else None
        if not current_user:
            return http_api.RedirectResponse(url="/login", status_code=302)
        
        try:
            html_content = await panel_service.render_panel_view(
                "dashboard.html",
                {"module_name": "user_panel"},
                request
            )
            return http_api.HTMLResponse(content=html_content)
        except Exception as e:
            if logger:
                logger.log(f"Error rendering dashboard: {e}", level="ERROR", tag="panel")
            return http_api.HTMLResponse(
                content="<h1>500 - Internal Server Error</h1><p>Failed to load dashboard.</p>",
                status_code=500
            )