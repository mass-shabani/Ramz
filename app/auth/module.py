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
    name = "auth"
    provides = ["auth_service"]
    requires = ["core_logger", "http_api", "template_service", "app_db_service"]

    def __init__(self):
        self.logger = None
        self.http_api = None
        self.template_service = None
        self.app_db_service = None
        self.auth_service = None

    async def load(self, context: ModuleContext):
        """Get services from context."""
        self.logger = context.services.get("core_logger")
        self.http_api = context.services.get("http_api")
        self.template_service = context.services.get("template_service")
        self.app_db_service = context.services.get("app_db_service")
        
        if self.logger:
            self.logger.log("Auth module loaded", tag="auth")

    async def start(self, context: ModuleContext):
        """Register auth routes and menu items."""
        if not self.http_api or not self.template_service or not self.app_db_service:
            if self.logger:
                self.logger.log("Required services not available, cannot start auth module", 
                              level="ERROR", tag="auth")
            return

        # Initialize auth service
        self.auth_service = AuthService(self.app_db_service, self.logger)
        context.services.set("auth_service", self.auth_service)

        # Register template directory
        templates_dir = str(Path(__file__).parent / "templates")
        self.template_service.register_template_directory(templates_dir, "auth")

        # Register menu items
        self.template_service.register_menu_item(
            menu_id="main_nav",
            item_id="auth_login",
            label="ورود",
            url="/login",
            order=900
        )
        self.template_service.register_menu_item(
            menu_id="main_nav",
            item_id="auth_logout",
            label="خروج",
            url="/logout",
            order=999
        )

        # --- Register Routes using http_api ---

        # GET /login - Login page
        @self.http_api.get("/login", response_class=self.http_api.HTMLResponse)
        async def login_page(request: self.http_api.Request):
            """Display the login page."""
            # Check if already logged in
            current_user = request.session.get("user") if hasattr(request, "session") else None
            if current_user:
                return self.http_api.RedirectResponse(url="/panel", status_code=302)
            
            html = await self.template_service.render(
                "login.html",
                context={
                    "current_user": None,
                    "error": None,
                    "module_name": "auth"
                }
            )
            return self.http_api.HTMLResponse(content=html)

        # POST /login - Handle login submission
        @self.http_api.post("/login", response_class=self.http_api.HTMLResponse)
        async def login_post(request: self.http_api.Request):
            """Handle login form submission."""
            form_data = await request.form()
            username = form_data.get("username", "")
            password = form_data.get("password", "")

            # Authenticate user via auth_service
            user = await self.auth_service.authenticate(username, password)

            if user:
                # Set session
                if hasattr(request, "session"):
                    request.session["user"] = {
                        "id": user["id"],
                        "username": user["username"],
                        "email": user["email"]
                    }
                
                if self.logger:
                    self.logger.log(f"User '{username}' logged in successfully", tag="auth")
                
                return self.http_api.RedirectResponse(url="/panel", status_code=302)
            else:
                if self.logger:
                    self.logger.log(f"Failed login attempt for '{username}'", level="WARNING", tag="auth")
                
                html = await self.template_service.render(
                    "login.html",
                    context={
                        "current_user": None,
                        "error": "نام کاربری یا رمز عبور اشتباه است.",
                        "module_name": "auth"
                    }
                )
                return self.http_api.HTMLResponse(content=html)

        # GET /logout - Logout user
        @self.http_api.get("/logout")
        async def logout(request: self.http_api.Request):
            """Clear user session and redirect to home."""
            if hasattr(request, "session"):
                user = request.session.get("user")
                if user and self.logger:
                    self.logger.log(f"User '{user.get('username')}' logged out", tag="auth")
                request.session.clear()
            
            return self.http_api.RedirectResponse(url="/", status_code=302)

        if self.logger:
            self.logger.log("Auth module routes registered successfully", tag="auth")

    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("Auth module stopped", tag="auth")