"""
Admin Panel Module

Provides a standalone administrative interface at /settings/admin
for managing users, forms, access grants, and roles.

Registers an extension in component_service so that an entry appears
in the user dropdown menu for users with access. The extension is
resolved per-request by component_service.prepare_context() based on
the "admin_panel.view" form grant.

When this module is disabled (removed from app_settings.json), the
extension disappears automatically and no route is registered.
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
        logger            = context.services.get("core_logger")
        http_api          = context.services.get("http_api")
        template_service  = context.services.get("template_service")
        db_service        = context.services.get("app_db_service")
        message_service   = context.services.get("message_service")
        component_service = context.services.get("component_service")

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
                        "table",
                    ]),
                )
                if logger:
                    logger.log(
                        "Admin Panel will load components: brand, user-menu, "
                        "card, topbar, progress-bar, content-container, dialog, table",
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
        # Extension registration (replaces panel_service.register_feature)
        # ------------------------------------------------------------
        if component_service:
            try:
                registered = component_service.register_extension(
                    point="ui.user_menu.items",
                    data={
                        "label": "Admin Panel",
                        "url": "/settings/admin",
                        "icon": "🛡️",
                        "order": 10,
                    },
                    form_id="admin_panel.view",
                    module_name="admin_panel",
                )
                if logger:
                    if registered:
                        logger.log(
                            "Admin Panel extension registered in user menu",
                            tag="admin",
                        )
                    else:
                        logger.log(
                            "Admin Panel extension NOT registered "
                            "(unknown extension point)",
                            level="WARNING",
                            tag="admin",
                        )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"Failed to register extension: {exc}",
                        level="ERROR",
                        tag="admin",
                    )


        else:
            if logger:
                logger.log(
                    "component_service not available — admin panel will not "
                    "appear in user menu, but routes will still work",
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
                component_service=component_service,
                app=context.get_app(),
                admin_service=admin_service,
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
