"""
Template and Menu Managers - Core classes for handling Jinja2 templates,
asset registration, menu registry, and logical asset mapping.
"""
from typing import Dict, List, Any
from pathlib import Path
import jinja2


class AssetService:
    """
    Provides logical mapping of asset names to their public URLs.
    Other modules use this service to get URLs for assets without knowing physical paths.
    """
    
    def __init__(self, logger):
        self.logger = logger
        # Mapping logical names to public URLs
        self._assets = {
            "favicon": "/static/assets/favicon.svg",
            "logo": "/static/images/logo.svg",
            "theme_css": "/static/css/theme.css",
            "theme_js": "/static/js/theme.js"
        }

    def get_url(self, asset_name: str) -> str:
        """Get the public URL for a logical asset name."""
        url = self._assets.get(asset_name, "")
        if not url and self.logger:
            self.logger.log(f"Asset '{asset_name}' not found in registry", 
                          level="WARNING", tag="assets")
        return url

    def register_asset(self, asset_name: str, public_url: str):
        """Register a new asset mapping."""
        self._assets[asset_name] = public_url


class TemplateManager:
    """
    Manages Jinja2 environment, template directories, and asset registration.
    """
    
    def __init__(self, templates_dir: Path, logger):
        self.logger = logger
        self.templates_dir = templates_dir
        self.additional_dirs: List[Path] = []
        self.global_css: List[str] = []
        self.global_js: List[str] = []
        self.module_assets: Dict[str, Dict[str, List[str]]] = {}
        
        self.env = self._create_jinja_env()
        self._register_default_assets()

    def _create_jinja_env(self) -> jinja2.Environment:
        """Create Jinja2 environment with all registered template directories."""
        loaders = [jinja2.FileSystemLoader(str(self.templates_dir))]
        for dir_path in self.additional_dirs:
            loaders.append(jinja2.FileSystemLoader(str(dir_path)))
        
        loader = jinja2.ChoiceLoader(loaders) if len(loaders) > 1 else loaders[0]
        
        env = jinja2.Environment(
            loader=loader,
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            enable_async=True
        )
        
        env.globals['get_global_css'] = lambda: self.global_css
        env.globals['get_global_js'] = lambda: self.global_js
        env.globals['get_module_assets'] = self.get_module_assets
        
        return env

    def register_template_directory(self, directory: str, module_name: str = None):
        """Register a template directory from another module."""
        dir_path = Path(directory).resolve()
        if dir_path not in self.additional_dirs:
            self.additional_dirs.append(dir_path)
            self.env = self._create_jinja_env()
            if self.logger:
                self.logger.log(f"Template directory registered: {dir_path.name} (module: {module_name})", 
                              tag="template")

    def register_module_assets(self, module_name: str, css_files: List[str] = None, js_files: List[str] = None):
        """Register CSS and JS assets for a specific module."""
        if module_name not in self.module_assets:
            self.module_assets[module_name] = {"css": [], "js": []}
        
        if css_files:
            for css in css_files:
                if css not in self.module_assets[module_name]["css"]:
                    self.module_assets[module_name]["css"].append(css)
        if js_files:
            for js in js_files:
                if js not in self.module_assets[module_name]["js"]:
                    self.module_assets[module_name]["js"].append(js)

    def register_global_css(self, css_path: str):
        """Register a global CSS file to be loaded on every page."""
        if css_path not in self.global_css:
            self.global_css.append(css_path)
            self.env = self._create_jinja_env()

    def register_global_js(self, js_path: str):
        """Register a global JS file to be loaded on every page."""
        if js_path not in self.global_js:
            self.global_js.append(js_path)
            self.env = self._create_jinja_env()

    def get_module_assets(self, module_name: str) -> Dict[str, List[str]]:
        """Get all registered assets for a specific module."""
        return self.module_assets.get(module_name, {"css": [], "js": []})

    def _register_default_assets(self):
        """Register the default global assets from template_service itself."""
        self.global_css = ["/static/css/theme.css"]
        self.global_js = ["/static/js/theme.js"]

    async def render(self, template_name: str, context: Dict[str, Any] = None) -> str:
        """
        Render a template with the given context.
        Returns the rendered HTML string.
        """
        try:
            # CORRECTION: get_template is synchronous, do NOT use await here
            template = self.env.get_template(template_name)
            
            # render_async is the actual asynchronous method
            return await template.render_async(context or {})
            
        except jinja2.TemplateNotFound as e:
            if self.logger:
                self.logger.log(f"Template not found: {template_name}", level="ERROR", tag="template")
            return f"<h1>Template Error: '{template_name}' not found</h1>"
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error rendering template {template_name}: {e}", level="ERROR", tag="template")
            return f"<h1>Template Rendering Error: {e}</h1>"


class MenuManager:
    """
    Manages menu items (navigation bar, sidebar, user panel) for the application.
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.menu_items: Dict[str, List[Dict[str, Any]]] = {
            "main_nav": [],
            "sidebar": [],
            "user_panel": [],
            "footer": []
        }

    def register_menu_item(self, menu_id: str, item_id: str, label: str, url: str, 
                          icon: str = None, tooltip: str = None, order: int = 100,
                          required_permission: str = None, badge: str = None):
        """Register a menu item to a specific menu area."""
        if menu_id not in self.menu_items:
            self.menu_items[menu_id] = []
        
        item_data = {
            "id": item_id, "label": label, "url": url, "icon": icon,
            "tooltip": tooltip, "order": order, "required_permission": required_permission, "badge": badge
        }
        
        for i, item in enumerate(self.menu_items[menu_id]):
            if item["id"] == item_id:
                self.menu_items[menu_id][i] = item_data
                self._sort_menu(menu_id)
                return
        
        self.menu_items[menu_id].append(item_data)
        self._sort_menu(menu_id)

    def unregister_menu_item(self, menu_id: str, item_id: str):
        """Remove a menu item from a specific menu area."""
        if menu_id in self.menu_items:
            self.menu_items[menu_id] = [item for item in self.menu_items[menu_id] if item["id"] != item_id]

    def _sort_menu(self, menu_id: str):
        """Sort menu items by their order value."""
        if menu_id in self.menu_items:
            self.menu_items[menu_id].sort(key=lambda x: x["order"])

    def get_menu_items(self, menu_id: str) -> List[Dict[str, Any]]:
        """Get all menu items for a specific menu area."""
        return self.menu_items.get(menu_id, [])
    """
    Manages menu items (navigation bar, sidebar, user panel) for the application.
    Other modules register their menu items here to appear in the UI.
    """
    
    def __init__(self, logger):
        self.logger = logger
        # Pre-defined menu areas in the application
        self.menu_items: Dict[str, List[Dict[str, Any]]] = {
            "main_nav": [],      # Top navigation bar
            "sidebar": [],       # Sidebar in user panel
            "user_panel": [],    # User panel specific items
            "footer": []         # Footer links
        }

    def register_menu_item(self, menu_id: str, item_id: str, label: str, url: str, 
                          icon: str = None, tooltip: str = None, order: int = 100,
                          required_permission: str = None, badge: str = None):
        """
        Register a menu item to a specific menu area.
        
        Args:
            menu_id: The area to add the item (e.g., 'sidebar', 'main_nav')
            item_id: Unique identifier for the menu item
            label: Display text
            url: Target URL
            icon: Icon class or emoji
            tooltip: Tooltip text
            order: Display order (lower numbers appear first)
            required_permission: Permission required to see this item
            badge: Optional badge text (e.g., notification count)
        """
        if menu_id not in self.menu_items:
            self.menu_items[menu_id] = []
        
        item_data = {
            "id": item_id,
            "label": label,
            "url": url,
            "icon": icon,
            "tooltip": tooltip,
            "order": order,
            "required_permission": required_permission,
            "badge": badge
        }
        
        # Check if item already exists (update it)
        for i, item in enumerate(self.menu_items[menu_id]):
            if item["id"] == item_id:
                self.menu_items[menu_id][i] = item_data
                self._sort_menu(menu_id)
                return
        
        # Add new item
        self.menu_items[menu_id].append(item_data)
        self._sort_menu(menu_id)

    def unregister_menu_item(self, menu_id: str, item_id: str):
        """Remove a menu item from a specific menu area."""
        if menu_id in self.menu_items:
            self.menu_items[menu_id] = [
                item for item in self.menu_items[menu_id] if item["id"] != item_id
            ]

    def _sort_menu(self, menu_id: str):
        """Sort menu items by their order value."""
        if menu_id in self.menu_items:
            self.menu_items[menu_id].sort(key=lambda x: x["order"])

    def get_menu_items(self, menu_id: str) -> List[Dict[str, Any]]:
        """Get all menu items for a specific menu area."""
        return self.menu_items.get(menu_id, [])

    def get_all_menus(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all registered menus."""
        return self.menu_items