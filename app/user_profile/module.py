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
        # Routes
        # ------------------------------------------------------------
        register_routes(http_api, template_service, db_service, logger)

        if logger:
            logger.log("User Profile module started", tag="profile")

    async def stop(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("User Profile module stopped", tag="profile")
