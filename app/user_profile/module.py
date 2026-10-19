"""
User Profile Module

Provides a standalone `/profile` page that renders the authenticated
user's personal and contact information.

The page is NOT part of the panel shell — it has its own topbar and
no sidebar. It is reachable via the user dropdown menu.
"""
from pathlib import Path

from massir.core.interfaces import IModule, ModuleContext
from .routes import register_routes


class UserProfileModule(IModule):
    """
    User profile module.
    Registers the /profile route and the profile template directory.
    """

    async def start(self, context: ModuleContext):
        logger           = context.services.get("core_logger")
        http_api         = context.services.get("http_api")
        template_service = context.services.get("template_service")
        db_service       = context.services.get("app_db_service")
        message_service  = context.services.get("message_service")

        if logger:
            logger.log("User Profile module starting…", tag="profile")

        if not all([http_api, template_service, db_service]):
            if logger:
                logger.log(
                    "Required services not available — cannot start user_profile",
                    level="ERROR",
                    tag="profile",
                )
            return

        # ------------------------------------------------------------
        # Template directory
        # ------------------------------------------------------------
        templates_dir = str(Path(__file__).parent / "templates")
        template_service.register_template_directory(
            templates_dir, "user_profile"
        )

        # ------------------------------------------------------------
        # Component registration (only what this module needs)
        # ------------------------------------------------------------
        component_service = context.services.get("component_service")
        if component_service:
            template_service.register_module_assets(
                "user_profile",
                js_files=component_service.get_component_urls([
                    "brand",
                    "user-menu",
                    "card",
                    "topbar",
                ]),
            )
            if logger:
                logger.log(
                    "User Profile will load components: "
                    "brand, user-menu, card, topbar",
                    tag="profile",
                )
        else:
            if logger:
                logger.log(
                    "component_service not available — profile will be static",
                    level="ERROR",
                    tag="profile",
                )

        # ------------------------------------------------------------
        # Routes
        # ------------------------------------------------------------
        register_routes(
            http_api,
            template_service,
            db_service,
            logger,
            message_service=message_service,
        )

        if logger:
            logger.log("User Profile module started", tag="profile")

    async def stop(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("User Profile module stopped", tag="profile")
