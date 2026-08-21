"""
User Info Routes - Defines HTTP endpoints for profile management.
"""
from typing import Any


def register_routes(http_api: Any, panel_service: Any, user_info_service: Any, logger: Any):
    """
    Register user info routes with the HTTP API.
    """
    
    @http_api.get("/panel/profile", response_class=http_api.HTMLResponse)
    async def profile_page(request: http_api.Request):
        """Display the user profile page."""
        current_user = request.session.get("user") if hasattr(request, "session") else None
        if not current_user:
            return http_api.RedirectResponse(url="/login", status_code=302)
        
        try:
            # Fetch latest data from database
            profile_data = await user_info_service.get_profile_data(current_user["id"])
            
            context = {
                "module_name": "user_info",
                "profile_data": profile_data,
                "success_message": None,
                "error_message": None
            }
            
            html_content = await panel_service.render_panel_view(
                "profile.html",
                context,
                request
            )
            return http_api.HTMLResponse(content=html_content)
            
        except Exception as e:
            if logger:
                logger.log(f"Error rendering profile page: {e}", level="ERROR", tag="user_info")
            return http_api.HTMLResponse(
                content="<h1>500 - Internal Server Error</h1><p>Failed to load profile.</p>",
                status_code=500
            )

    @http_api.post("/panel/profile", response_class=http_api.HTMLResponse)
    async def profile_update(request: http_api.Request):
        """Handle user profile update form submission."""
        current_user = request.session.get("user") if hasattr(request, "session") else None
        if not current_user:
            return http_api.RedirectResponse(url="/login", status_code=302)
        
        try:
            form_data = await request.form()
            new_email = form_data.get("email", "").strip()
            
            if not new_email:
                context = {
                    "module_name": "user_info",
                    "profile_data": await user_info_service.get_profile_data(current_user["id"]),
                    "success_message": None,
                    "error_message": "Please enter a valid email address."
                }
                html_content = await panel_service.render_panel_view("profile.html", context, request)
                return http_api.HTMLResponse(content=html_content)

            success, message = await user_info_service.update_profile(current_user["id"], new_email)
            
            # Refresh data for the view
            profile_data = await user_info_service.get_profile_data(current_user["id"])
            
            context = {
                "module_name": "user_info",
                "profile_data": profile_data,
                "success_message": message if success else None,
                "error_message": message if not success else None
            }
            
            html_content = await panel_service.render_panel_view("profile.html", context, request)
            return http_api.HTMLResponse(content=html_content)
            
        except Exception as e:
            if logger:
                logger.log(f"Error processing profile update: {e}", level="ERROR", tag="user_info")
            return http_api.HTMLResponse(
                content="<h1>500 - Internal Server Error</h1><p>Failed to update profile.</p>",
                status_code=500
            )