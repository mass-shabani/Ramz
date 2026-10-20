"""
Admin Panel Module

Provides a standalone administrative interface at /settings/admin
for managing users, forms, access grants, and roles.

The module registers a feature in `panel_service` so that a link
appears in the user dropdown menu for users with access. When the
module is disabled (removed from app_settings.json), the feature
link disappears automatically and no route is registered — this
is the graceful-degradation contract.
"""
from pathlib import Path

from massir.core.interfaces import IModule, ModuleContext
from .services import AdminPanelService
from .routes import register_routes


class AdminPanelModule(IModule):
    """
    Admin Panel module.
    """

    async def start(self, context: ModuleContext):
        logger           = context.services.get("core_logger")
        http_api         = context.services.get("http_api")
        template_service = context.services.get("template_service")
        db_service       = context.services.get("app_db_service")
        message_service  = context.services.get("message_service")
        component_service = context.services.get("component_service")
        panel_service    = context.services.get("panel_service")

        if logger:
            logger.log("Admin Panel module starting…", tag="admin")

        # ------------------------------------------------------------
        # Guard: essential services
        # ------------------------------------------------------------
        if not all([http_api, template_service, db_service]):
            if logger:
                logger.log(
                    "Required services not available — cannot start admin_panel",
                    level="ERROR",
                    tag="admin",
                )
            return

        # ------------------------------------------------------------
        # Service
        # ------------------------------------------------------------
        try:
            admin_service = AdminPanelService(
                db_service=db_service,
                template_service=template_service,
                logger=logger,
            )
            context.services.set("admin_panel_service", admin_service)
        except Exception as exc:
            if logger:
                logger.log(
                    f"Failed to register admin_panel_service: {exc}",
                    level="ERROR",
                    tag="admin",
                )
            return

        # ------------------------------------------------------------
        # Template directory
        # ------------------------------------------------------------
        templates_dir = str(Path(__file__).parent / "templates")
        template_service.register_template_directory(
            templates_dir, "admin_panel"
        )

        # ------------------------------------------------------------
        # Components (only what this module uses)
        # ------------------------------------------------------------
        if component_service:
            try:
                template_service.register_module_assets(
                    "admin_panel",
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
                        "Admin Panel will load components: brand, user-menu, "
                        "card, topbar, progress-bar, content-container, dialog",
                        tag="admin",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"Failed to register components: {exc}",
                        level="ERROR",
                        tag="admin",
                    )

        # ------------------------------------------------------------
        # Feature registry — adds link to user-menu
        # ------------------------------------------------------------
        if panel_service:
            try:
                panel_service.register_feature(
                    name="admin_panel",
                    url="/settings/admin",
                    label="Admin Panel",
                    icon="🛡️",
                    form_id="admin_panel.view",
                    condition="Full",
                )
                if logger:
                    logger.log(
                        "Admin Panel feature registered in panel_service",
                        tag="admin",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"Failed to register feature: {exc}",
                        level="ERROR",
                        tag="admin",
                    )
        else:
            if logger:
                logger.log(
                    "panel_service not available — admin panel will not appear "
                    "in user menu, but routes will still work",
                    level="WARNING",
                    tag="admin",
                )

        # ------------------------------------------------------------
        # Routes
        # ------------------------------------------------------------
        try:
            register_routes(
                http_api=http_api,
                template_service=template_service,
                db_service=db_service,
                logger=logger,
                message_service=message_service,
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"Failed to register routes: {exc}",
                    level="ERROR",
                    tag="admin",
                )
            return

        if logger:
            logger.log("Admin Panel module started", tag="admin")

    async def stop(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("Admin Panel module stopped", tag="admin")
