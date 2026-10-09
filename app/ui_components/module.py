"""
UI Components Module

Registers the shared web components library with the template service
and exposes a `component_service` that other modules can use to load
specific components or the full bundle.
"""
from pathlib import Path

from massir.core.interfaces import IModule, ModuleContext

from .services import ComponentService


class UIComponentsModule(IModule):
    """
    UI components module.

    Responsibilities:
        • Register the module's static directory.
        • Instantiate ComponentService and expose it as `component_service`.
        • (Future) Register any module-specific CSS if added later.

    This module does NOT register routes and does NOT register any
    templates. It only serves static JS files and the service.
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

        if logger:
            count = len(component_service.get_all_components())
            logger.log(
                f"Component service registered with {count} components",
                tag="ui",
            )

        if logger:
            logger.log("UI Components module started successfully", tag="ui")

    async def stop(self, context: ModuleContext):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("UI Components module stopped", tag="ui")
