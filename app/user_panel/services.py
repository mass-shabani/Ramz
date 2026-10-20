"""
Panel Service - Handles rendering of panel views with the sidebar layout.
"""
from typing import Any, Dict


class PanelService:
    """
    Provides methods to render module views inside the panel layout.
    Other modules (like user_info) use this service to display their content in the panel.
    """
    
    def __init__(self, template_service: Any, menu_manager: Any, logger: Any):
        self.template_service = template_service
        self.menu_manager = menu_manager
        self.logger = logger
        self._features = {}

    # ============================================================
    # Feature registry
    # ============================================================
    def register_feature(
        self,
        name: str,
        url: str,
        label: str,
        icon: str = "",
        form_id: str = None,
        condition: str = "Full",
    ) -> bool:
        """
        Register a feature link to be displayed in the user menu.

        Parameters
        ----------
        name : str
            Unique feature identifier (e.g. "admin_panel").
        url : str
            URL the link points to.
        label : str
            User-facing label.
        icon : str, optional
            Emoji or raw SVG markup.
        form_id : str, optional
            The form to check access against. Defaults to f"{name}.view".
        condition : str, optional
            The condition the form grant must equal. Defaults to "Full".
        """
        if not name or not url:
            return False

        self._features[name] = {
            "name":     name,
            "url":      url,
            "label":    label,
            "icon":     icon,
            "form_id":  form_id or f"{name}.view",
            "condition": condition,
        }
        if self.logger:
            try:
                self.logger.log(
                    f"Registered feature: {name} → {url}",
                    tag="panel",
                )
            except Exception:
                pass
        return True

    def unregister_feature(self, name: str) -> bool:
        """Remove a previously-registered feature."""
        return self._features.pop(name, None) is not None

    async def get_features_for_user(self, user_id, db_service):
        """
        Return the list of features the user has access to.
        """
        if not user_id or not db_service:
            return []

        result = []
        for name, feat in self._features.items():
            try:
                allowed = await db_service.has_access(
                    user_id, feat["form_id"]
                )
            except Exception:
                allowed = False

            if allowed:
                result.append({
                    "name":  feat["name"],
                    "url":   feat["url"],
                    "label": feat["label"],
                    "icon":  feat["icon"],
                })
        return result

    async def render_panel_view(self, template_name: str, context: Dict[str, Any], request: Any) -> str:
        """
        Render a module's template inside the panel layout, injecting sidebar items and user data.
        
        Args:
            template_name: The template to render (should extend 'panel_layout.html')
            context: Additional context variables for the template
            request: The HTTP request object (to access session)
            
        Returns:
            Rendered HTML string
        """
        current_user = request.session.get("user") if hasattr(request, "session") else None
        
        # Get sidebar items from menu_manager
        sidebar_items = self.menu_manager.get_menu_items("sidebar")
        
        # Prepare context for the panel layout
        panel_context = {
            "current_user": current_user,
            "sidebar_items": sidebar_items,
            "module_name": context.get("module_name", "user_panel"),
            "request": request,
            **context
        }
        
        try:
            return await self.template_service.render(template_name, panel_context)
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error rendering panel view: {e}", level="ERROR", tag="panel")
            return f"<h1>Error rendering panel view</h1><p>{e}</p>"