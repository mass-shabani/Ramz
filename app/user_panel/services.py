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
            **context
        }
        
        try:
            return await self.template_service.render(template_name, panel_context)
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error rendering panel view: {e}", level="ERROR", tag="panel")
            return f"<h1>Error rendering panel view</h1><p>{e}</p>"