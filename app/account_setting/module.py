"""
Account Setting Module

Provides the standalone `/settings/account` page where the authenticated
user can edit personal information, security, subscription, banking,
sessions, and delete their account.

The page is NOT part of the panel shell — it has its own topbar and
no sidebar. It is reachable via the user dropdown menu.

Extensions are resolved via component_service.prepare_context() in
routes.py and injected into the template context under "ui_extensions".
"""
from pathlib import Path

from massir.core.interfaces import IModule, ModuleContext
from .routes import register_routes


class AccountSettingModule(IModule):
    """
    Account Setting module.
    Registers the /settings/account route and the settings template.
    """

    async def start(self, context: ModuleContext):
        logger           = context.services.get("core_logger")
        http_api         = context.services.get("http_api")
        template_service = context.services.get("template_service")
        db_service       = context.services.get("app_db_service")
        message_service  = context.services.get("message_service")

        if logger:
            logger.log("Account Setting module starting…", tag="settings")

        if not all([http_api, template_service, db_service]):
            if logger:
                logger.log(
                    "Required services not available — cannot start account_setting",
                    level="ERROR",
                    tag="settings",
                )
            return

        # ------------------------------------------------------------
        # Template directory
        # ------------------------------------------------------------
        templates_dir = str(Path(__file__).parent / "templates")
        template_service.register_template_directory(
            templates_dir, "account_setting"
        )

        # ------------------------------------------------------------
        # Component registration (only what this module needs)
        # ------------------------------------------------------------
        component_service = context.services.get("component_service")
        if component_service:
            template_service.register_module_assets(
                "account_setting",
                js_files=component_service.get_component_urls([
                    "brand",
                    "user-menu",
                    "card",
                    "topbar",
                    "progress-bar",
                    "content-container",
                    "dialog",
                ]),
            )
            if logger:
                logger.log(
                    "Account Setting will load components: "
                    "brand, user-menu, card, topbar, progress-bar, content-container, dialog",
                    tag="settings",
                )
        else:
            if logger:
                logger.log(
                    "component_service not available — settings will be static",
                    level="ERROR",
                    tag="settings",
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
            logger.log("Account Setting module started", tag="settings")

    async def stop(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("Account Setting module stopped", tag="settings")
