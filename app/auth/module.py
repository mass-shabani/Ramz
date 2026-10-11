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

        # (Data seeding is the administrator's responsibility —
        #  see data/seed_auth.sql for the required forms.)

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
            """Display the login page (guarded by auth.login.view)."""
            # 1. Already logged in? → redirect to panel
            current_user = (
                request.session.get("user")
                if hasattr(request, "session")
                else None
            )
            if current_user:
                return http_api.RedirectResponse(url="/panel", status_code=302)

            # 2. Check public access
            allowed = await db_service.has_public_access("auth.login.view")
            if not allowed:
                # Login page closed by admin — likely a misconfiguration
                return http_api.HTMLResponse(
                    content="<h1>Login is temporarily unavailable</h1>",
                    status_code=503,
                )

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

        @http_api.get("/signup", response_class=http_api.HTMLResponse)
        async def signup_page(request: http_api.Request):
            """Display the signup page (guarded by auth.signup.view)."""
            # 1. Already logged in? → redirect
            current_user = (
                request.session.get("user")
                if hasattr(request, "session")
                else None
            )
            if current_user:
                return http_api.RedirectResponse(url="/panel", status_code=302)

            # 2. Check public access
            allowed = await db_service.has_public_access("auth.signup.view")
            if not allowed:
                return http_api.HTMLResponse(
                    content=(
                        "<h1>Sign-up is currently closed</h1>"
                        "<p>Please contact an administrator.</p>"
                    ),
                    status_code=403,
                )

            html = await template_service.render(
                "signup.html",
                context={
                    "current_user": None,
                    "error":        None,
                    "error_code":   None,
                    "form_data":    {},
                    "module_name":  "auth",
                },
            )
            return http_api.HTMLResponse(content=html)

        @http_api.post("/signup", response_class=http_api.HTMLResponse)
        async def signup_post(request: http_api.Request):
            """Handle signup form submission."""
            # Guard again — admin may have closed signup between GET and POST
            allowed = await db_service.has_public_access("auth.signup.view")
            if not allowed:
                return http_api.HTMLResponse(
                    content="<h1>Sign-up is currently closed</h1>",
                    status_code=403,
                )

            form_data = await request.form()

            # Collect fields
            username   = (form_data.get("username") or "").strip()
            password   = form_data.get("password") or ""
            password2  = form_data.get("password_confirm") or ""
            first_name = (form_data.get("first_name") or "").strip()
            last_name  = (form_data.get("last_name") or "").strip()
            email      = (form_data.get("email") or "").strip() or None
            phone      = (form_data.get("phone") or "").strip() or None

            # Render the form back with data preserved on error
            async def render_with_error(code: str, message: str):
                return await template_service.render(
                    "signup.html",
                    context={
                        "current_user": None,
                        "error":        message,
                        "error_code":   code,
                        "form_data": {
                            "username":   username,
                            "first_name": first_name,
                            "last_name":  last_name,
                            "email":      email or "",
                            "phone":      phone or "",
                        },
                        "module_name": "auth",
                    },
                )

            # Local validation
            if not all([username, password, first_name, last_name]):
                html = await render_with_error(
                    "missing_fields",
                    "Please fill in all required fields.",
                )
                return http_api.HTMLResponse(content=html)

            if password != password2:
                html = await render_with_error(
                    "password_mismatch",
                    "The two passwords do not match.",
                )
                return http_api.HTMLResponse(content=html)

            if len(password) < 8:
                html = await render_with_error(
                    "weak_password",
                    "Password must be at least 8 characters long.",
                )
                return http_api.HTMLResponse(content=html)

            # Build SignupData
            from app.db_manager.models.signup import SignupData
            from app.db_manager.workflows import SignupError

            data = SignupData(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
            )

            try:
                user = await db_service.create_account(data)
            except SignupError as exc:
                message_map = {
                    "username_exists": "This username is already taken.",
                    "email_exists":    "This email is already registered.",
                    "role_not_found":  "Configuration error. Contact support.",
                    "internal_error":  "Something went wrong. Please try again.",
                }
                html = await render_with_error(
                    exc.code,
                    message_map.get(exc.code, "Signup failed."),
                )
                return http_api.HTMLResponse(content=html)

            if logger:
                logger.log(
                    f"New account created: {username} (user_id={user.user_id})",
                    tag="auth",
                )

            # Auto-login: authenticate immediately
            try:
                await auth_service.login(username, password, request)
                return http_api.RedirectResponse(url="/panel", status_code=302)
            except Exception as exc:
                if logger:
                    logger.log(
                        f"Auto-login after signup failed: {exc}",
                        level="WARNING",
                        tag="auth",
                    )
                return http_api.RedirectResponse(url="/login", status_code=302)

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