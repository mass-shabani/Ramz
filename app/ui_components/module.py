"""
UI Components Module

Registers the shared web components library with the template service
and exposes a `component_service` that other modules can use to load
specific components or the full bundle.

Also exposes `ui_hooks` (dict with HOOK_COLLECT and HOOK_RESOLVE) so
other modules can register callbacks for extension resolution without
importing from this module directly.

HOOK_COLLECT is fired once at ON_ALL_MODULES_STARTED. This gives late
modules a chance to batch-register contributions even if they started
after ui_components.
"""
from pathlib import Path

from massir.core.interfaces import IModule, ModuleContext
from massir.core.hook_types import SystemHook

from .extensions import HOOK_COLLECT, HOOK_RESOLVE
from .services import ComponentService


class UIComponentsModule(IModule):
    """
    UI components module.

    Responsibilities:
        • Register the module's static directory.
        • Instantiate ComponentService and expose it as `component_service`.
        • Expose `ui_hooks` (HOOK_COLLECT, HOOK_RESOLVE) for other modules.
        • Fire HOOK_COLLECT at ON_ALL_MODULES_STARTED.
    """

    async def start(self, context: ModuleContext):
        logger           = context.services.get("core_logger")
        template_service = context.services.get("template_service")

        if logger:
            logger.log("UI Components module starting…", tag="ui")

        # ------------------------------------------------------------
        # Static directory
        # ------------------------------------------------------------
        if template_service and hasattr(template_service, "register_module_static_directory"):
            static_dir = str(Path(__file__).parent / "static")
            template_service.register_module_static_directory(
                "ui_components",
                static_dir,
            )
            if logger:
                logger.log(
                    f"Registered static directory: {static_dir}",
                    tag="ui",
                )
        else:
            if logger:
                logger.log(
                    "template_service not available — static files will not be served",
                    level="ERROR",
                    tag="ui",
                )

        # ------------------------------------------------------------
        # Component service
        # ------------------------------------------------------------
        component_service = ComponentService(logger=logger)
        context.services.set("component_service", component_service)

        # ------------------------------------------------------------
        # UI hooks registry
        # ------------------------------------------------------------
        context.services.set("ui_hooks", {
            "collect": HOOK_COLLECT,
            "resolve": HOOK_RESOLVE,
        })

        if logger:
            count = len(component_service.get_all_components())
            logger.log(
                f"Component service registered with {count} components",
                tag="ui",
            )

        # ------------------------------------------------------------
        # Fire HOOK_COLLECT at ON_ALL_MODULES_STARTED
        # ------------------------------------------------------------
        app = context.get_app()
        if app is not None:
            async def _fire_collect():
                try:
                    await app.trigger_hook(
                        HOOK_COLLECT,
                        registry=component_service.registry,
                    )
                except Exception as e:
                    if logger:
                        logger.log(
                            f"HOOK_COLLECT failed: {e}",
                            level="ERROR",
                            tag="ui",
                        )

            app.register_hook(SystemHook.ON_ALL_MODULES_STARTED, _fire_collect)

            if logger:
                logger.log(
                    "HOOK_COLLECT registered for ON_ALL_MODULES_STARTED",
                    tag="ui",
                )

        if logger:
            logger.log("UI Components module started successfully", tag="ui")

    async def stop(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("UI Components module stopped", tag="ui")
