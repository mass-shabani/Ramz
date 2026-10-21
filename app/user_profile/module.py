"""
User Profile Module

Provides a standalone `/profile` page that renders the authenticated
user's personal and contact information.

The page is NOT part of the panel shell — it has its own topbar and
no sidebar. It is reachable via the user dropdown menu.

Extensions are resolved via component_service.prepare_context() in
routes.py and injected into the template context under "ui_extensions".
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
        logger            = context.services.get("core_logger")
        http_api          = context.services.get("http_api")
        template_service  = context.services.get("template_service")
        db_service        = context.services.get("app_db_service")
        message_service   = context.services.get("message_service")
        component_service = context.services.get("component_service")

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

            # ------------------------------------------------------
            # Topbar action: "Back to Panel"
            # ------------------------------------------------------
            try:
                component_service.register_extension(
                    point="ui.topbar.actions",
                    data={
                        "href": "/panel",
                        "title": "Back to Panel",
                        "aria_label": "Back to Panel",
                        "icon": (
                            '<svg viewBox="0 0 24 24" fill="none" '
                            'stroke="currentColor" stroke-width="1.9" '
                            'stroke-linecap="round" stroke-linejoin="round">'
                            '<rect x="3" y="3" width="7" height="9" rx="2"/>'
                            '<rect x="14" y="3" width="7" height="5" rx="2"/>'
                            '<rect x="14" y="12" width="7" height="9" rx="2"/>'
                            '<rect x="3" y="16" width="7" height="5" rx="2"/>'
                            '</svg>'
                        ),
                        "order": 100,
                    },
                    form_id=None,
                    module_name="user_profile",
                )
                if logger:
                    logger.log(
                        "User Profile topbar action registered",
                        tag="profile",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"Failed to register topbar action: {exc}",
                        level="ERROR",
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
            component_service=component_service,
            app=context.get_app(),
        )

        if logger:
            logger.log("User Profile module started", tag="profile")

    async def stop(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("User Profile module stopped", tag="profile")
