"""
Global Router - Pure infrastructure for route management.
Handles error delegation to message_view and provides helper methods.
"""
from typing import Any, Callable


class GlobalRouter:
    """
    Handles global route registration, error delegation, and provides a helper interface.
    """
    
    def __init__(self, http_api: Any, message_service: Any, logger: Any):
        self.http_api = http_api
        self.message_service = message_service
        self.logger = logger

    def register_global_endpoints(self):
        """Register global error handlers (delegates rendering to message_view)."""
        self._register_error_handlers()

    def _register_error_handlers(self):
        """Register custom error handlers using http_api service."""
        try:
            app = self._get_fastapi_app()
            if not app:
                return

            # Register exception handlers via the underlying app or http_api if supported
            @app.exception_handler(404)
            async def custom_404_handler(request, exc):
                html = await self.message_service.render_message(
                    status_code=404,
                    title="Page Not Found",
                    message="The page you are looking for does not exist.",
                    message_type="error"
                )
                # Use http_api's HTMLResponse
                return self.http_api.HTMLResponse(content=html, status_code=404)

            @app.exception_handler(500)
            async def custom_500_handler(request, exc):
                html = await self.message_service.render_message(
                    status_code=500,
                    title="Internal Server Error",
                    message="Something went wrong on our end. Please try again later.",
                    message_type="error"
                )
                return self.http_api.HTMLResponse(content=html, status_code=500)

        except Exception as e:
            if self.logger:
                self.logger.log(f"Could not register custom error handlers: {e}", 
                              level="WARNING", tag="routes")

    def _get_fastapi_app(self):
        """Retrieve the underlying application instance."""
        if hasattr(self.http_api, 'get_app'):
            return self.http_api.get_app()
        elif hasattr(self.http_api, 'app'):
            return self.http_api.app
        return None

    # --- Helper Methods for Other Modules ---
    
    def register_route(self, method: str, path: str, handler: Callable, **kwargs):
        """Helper method for other modules to register routes consistently."""
        decorator_map = {
            "GET": self.http_api.get,
            "POST": self.http_api.post,
            "PUT": self.http_api.put,
            "DELETE": self.http_api.delete,
            "PATCH": self.http_api.patch,
        }
        
        decorator = decorator_map.get(method.upper())
        if decorator:
            decorator(path, **kwargs)(handler)
            if self.logger:
                self.logger.log(f"Route registered: {method.upper()} {path}", tag="routes")
        else:
            if self.logger:
                self.logger.log(f"Unsupported HTTP method: {method}", 
                              level="WARNING", tag="routes")