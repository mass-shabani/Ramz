"""
Auth Module - Handles user authentication, login, logout, and session management.
"""
from pathlib import Path

from massir.core.interfaces import IModule, ModuleContext
from .services import AuthService


class AuthModule(IModule):
    """
    Auth module.
    Provides auth_service and registers authentication routes.
    """

    async def start(self, context: ModuleContext):
        """Get services, initialize auth service, register routes and menu items."""
        logger = context.services.get("core_logger")
        http_api = context.services.get("http_api")
        template_service = context.services.get("template_service")
        menu_manager = context.services.get("menu_manager")

        # Central database service
        db_service = context.services.get("app_db_service")

        if logger:
            logger.log("Auth module started", tag="auth")

        if not all([http_api, template_service, menu_manager, db_service]):
            if logger:
                logger.log(
                    "Required services not available, cannot start auth module",
                    level="ERROR",
                    tag="auth",
                )
            return

        auth_service = AuthService(db_service, logger)
        context.services.set("auth_service", auth_service)

        templates_dir = str(Path(__file__).parent / "templates")
        template_service.register_template_directory(templates_dir, "auth")

        menu_manager.register_menu_item(
            menu_id="main_nav",
            item_id="auth_login",
            label="Login",
            url="/login",
            order=900,
        )
        menu_manager.register_menu_item(
            menu_id="main_nav",
            item_id="auth_logout",
            label="Logout",
            url="/logout",
            order=999,
        )

        @http_api.get("/login", response_class=http_api.HTMLResponse)
        async def login_page(request: http_api.Request):
            """Display the login page."""
            current_user = (
                request.session.get("user")
                if hasattr(request, "session")
                else None
            )
            if current_user:
                return http_api.RedirectResponse(url="/panel", status_code=302)

            html = await template_service.render(
                "login.html",
                context={
                    "current_user": None,
                    "error":        None,
                    "error_code":   None,
                    "username":     "",
                    "module_name":  "auth",
                },
            )
            return http_api.HTMLResponse(content=html)

        @http_api.post("/login", response_class=http_api.HTMLResponse)
        async def login_post(request: http_api.Request):
            """Handle login form submission."""
            form_data = await request.form()
            username = form_data.get("username", "")
            password = form_data.get("password", "")

            error_code = await auth_service.login(username, password, request)

            if error_code is None:
                if logger:
                    logger.log(
                        f"User '{username}' logged in successfully",
                        tag="auth",
                    )
                return http_api.RedirectResponse(url="/panel", status_code=302)

            if logger:
                logger.log(
                    f"Failed login attempt for '{username}': {error_code}",
                    level="WARNING",
                    tag="auth",
                )

            # Map error code to a user-facing message
            messages = {
                "invalid_credentials": "Invalid username or password.",
                "account_disabled":    "Your account has been disabled. Contact support.",
                "invalid_data":        "Please enter both username and password.",
                "internal_error":      "Something went wrong. Please try again later.",
            }
            error_message = messages.get(
                error_code, "Invalid username or password."
            )

            html = await template_service.render(
                "login.html",
                context={
                    "current_user": None,
                    "error":        error_message,
                    "error_code":   error_code,
                    "username":     username,
                    "module_name":  "auth",
                },
            )
            return http_api.HTMLResponse(content=html)

        @http_api.get("/logout")
        async def logout(request: http_api.Request):
            """Clear user session and redirect to home."""
            await auth_service.logout(request)
            return http_api.RedirectResponse(url="/", status_code=302)

        if logger:
            logger.log("Auth module routes registered successfully", tag="auth")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        logger = context.services.get("core_logger")
        if logger:
            logger.log("Auth module stopped", tag="auth")