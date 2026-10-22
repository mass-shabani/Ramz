"""
User Panel Module — Manages the user panel layout, sidebar navigation,
and the dashboard.

Provides:
    panel_service — for other modules to render their views inside the panel.
"""
from pathlib import Path

from massir.core.interfaces import IModule, ModuleContext
from .services import PanelService
from .routes import register_routes


class UserPanelModule(IModule):
    """
    User panel module.

    Registers templates, static files, component bundle, sidebar menu
    entries, and panel routes. Provides `panel_service` to the rest of
    the application.
    """

    async def start(self, context: ModuleContext):
        # ------------------------------------------------------------
        # Resolve required services from the context
        # ------------------------------------------------------------
        logger            = context.services.get("core_logger")
        http_api          = context.services.get("http_api")
        template_service  = context.services.get("template_service")
        menu_manager      = context.services.get("menu_manager")
        asset_service     = context.services.get("asset_service")
        message_service   = context.services.get("message_service")
        component_service = context.services.get("component_service")

        if logger:
            logger.log("UserPanel module starting…", tag="panel")

        # Fail fast if the essential services are missing
        if not http_api or not template_service or not menu_manager:
            if logger:
                logger.log(
                    "Required services not available, cannot start user_panel",
                    level="ERROR",
                    tag="panel"
                )
            return

        # ------------------------------------------------------------
        # Database service (for session validation)
        # ------------------------------------------------------------
        db_service = context.services.get("app_db_service")
        if not db_service:
            if logger:
                logger.log(
                    "app_db_service not available — session validation disabled",
                    level="ERROR",
                    tag="panel",
                )
            return

        # ------------------------------------------------------------
        # Panel service (exposed to other modules)
        # ------------------------------------------------------------
        panel_service = PanelService(template_service, menu_manager, logger)
        context.services.set("panel_service", panel_service)

        # ------------------------------------------------------------
        # Template directory
        # ------------------------------------------------------------
        templates_dir = str(Path(__file__).parent / "templates")
        template_service.register_template_directory(templates_dir, "user_panel")

        # ------------------------------------------------------------
        # Component bundle from ui_components
        # ------------------------------------------------------------
        if component_service:
            template_service.register_module_assets(
                "user_panel",
                js_files=[component_service.get_bundle_url()],
            )
            if logger:
                logger.log(
                    f"Panel will load bundle: {component_service.get_bundle_url()}",
                    tag="panel",
                )
        else:
            if logger:
                logger.log(
                    "component_service not available — panel components will not load",
                    level="ERROR",
                    tag="panel",
                )

        # ------------------------------------------------------------
        # Topbar action: "Back to Panel"
        # Registered once here (not per-page) and resolved on every page
        # that calls prepare_context with "ui.topbar.actions".
        # Hidden on /panel itself (via hide_on_path).
        # Access gated by "user_panel.view" — only users with access to
        # /panel will see this button.
        # ------------------------------------------------------------
        if component_service:
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
                        "hide_on_path": "/panel",
                        "order": 100,
                    },
                    form_id="user_panel.view",
                    module_name="user_panel",
                )
                if logger:
                    logger.log(
                        "User Panel topbar action registered",
                        tag="panel",
                    )
            except Exception as exc:
                if logger:
                    logger.log(
                        f"Failed to register topbar action: {exc}",
                        level="ERROR",
                        tag="panel",
                    )

        # ------------------------------------------------------------
        # Sidebar menu item (kept for compatibility — the visual sidebar
        # is now component-driven, but other modules may still enumerate
        # the "Dashboard" entry via menu_manager).
        # ------------------------------------------------------------
        try:
            menu_manager.register_menu_item(
                menu_id="sidebar",
                item_id="panel_dashboard",
                label="Dashboard",
                url="/panel",
                icon="🏠",
                tooltip="Panel Home",
                order=10,
            )
        except Exception as exc:
            if logger:
                logger.log(
                    f"Could not register sidebar menu item: {exc}",
                    level="WARNING",
                    tag="panel",
                )

        # ------------------------------------------------------------
        # Routes
        # ------------------------------------------------------------
        register_routes(
            http_api,
            panel_service,
            message_service,
            logger,
            db_service,
            component_service=component_service,
            app=context.get_app(),
            template_service=template_service,
        )

        if logger:
            logger.log("UserPanel module started successfully", tag="panel")

    async def stop(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("UserPanel module stopped", tag="panel")
