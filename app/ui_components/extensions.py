"""
Component Extension Registry

Defines the hooks and registry class used to declare and resolve
extensions to be injected into ui_components at render time.

Two-phase model:
  1. declare() - modules add contributions (at startup, from start())
  2. resolve() - per request, filter by access + sort by order

Hooks exposed:
  - HOOK_COLLECT: fired once at ON_ALL_MODULES_STARTED. Modules may
    use this to batch-register contributions if direct registration
    in start() is not convenient.
  - HOOK_RESOLVE: fired per-request inside ComponentService.prepare_context().
    Modules may use this to add dynamic, user-specific contributions.

Hooks are registered under the "ui_hooks" service key by the
ui_components module (see module.py). Consumers retrieve them via
context.services.get("ui_hooks").
"""

from typing import Any, Dict, List, Optional

from massir.core.hooks import Hook


HOOK_COLLECT = Hook("ui_components.collect")
HOOK_RESOLVE = Hook("ui_components.resolve")


class ComponentExtensionRegistry:
    """Central registry for component extensions."""

    KNOWN_POINTS = {
        "ui.user_menu.items",
        "ui.topbar.actions",
        "ui.topbar.center",
        "ui.topbar.start",
        "ui.sidebar.items",
        "ui.notifications.items",
        "ui.search.items",
    }

    def __init__(self, logger=None):
        self._logger = logger
        self._declarations: Dict[str, List[Dict[str, Any]]] = {}

    def declare(
        self,
        point: str,
        data: Dict[str, Any],
        form_id: Optional[str] = None,
        order: int = 100,
        module_name: Optional[str] = None,
    ) -> bool:
        """
        Declare an extension contribution for a known point.

        Returns True on success, False if the point is unknown.
        """
        if point not in self.KNOWN_POINTS:
            if self._logger:
                self._logger.log(
                    f"Unknown extension point: {point} "
                    f"(from module: {module_name or 'unknown'})",
                    level="WARNING",
                    tag="ui",
                )
            return False

        entry = {
            "data": data,
            "form_id": form_id,
            "order": data.get("order", order),
            "module": module_name,
        }
        self._declarations.setdefault(point, []).append(entry)
        return True

    async def resolve(
        self,
        points: List[str],
        user_id: Optional[str] = None,
        db_service=None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Resolve contributions for the given points, filtered by access
        and sorted by order.

        Access is fail-closed: if a contribution declares a form_id but
        no user_id or db_service is available, the contribution is skipped.
        """
        result: Dict[str, List[Dict[str, Any]]] = {}

        for point in points:
            entries = self._declarations.get(point, [])
            filtered: List[Dict[str, Any]] = []

            for entry in entries:
                form_id = entry["form_id"]
                if form_id:
                    if not user_id or not db_service:
                        continue
                    try:
                        allowed = await db_service.has_access(user_id, form_id)
                    except Exception:
                        allowed = False
                    if not allowed:
                        continue
                filtered.append(entry)

            filtered.sort(key=lambda e: e["order"])
            result[point] = [e["data"] for e in filtered]

        return result
