"""
UI Components Service

Provides a central registry of web components that other modules can
request by name. The service does not hold any files itself — it only
maps logical component names to their public URLs.
"""


class ComponentService:
    """
    Registry of web components available to the whole application.

    A component is identified by a short logical name (e.g. "card",
    "search", "sidebar") and mapped to a public URL served from the
    ui_components static directory.
    """

    # --------------------------------------------------------------
    # Default components shipped with this module.
    # Order does not matter.
    # --------------------------------------------------------------
    DEFAULT_COMPONENTS = {
        "brand":              "/static/ui_components/js/components/brand.js",
        "promo":              "/static/ui_components/js/components/promo.js",
        "card":               "/static/ui_components/js/components/card.js",
        "menu-group":         "/static/ui_components/js/components/menu-group.js",
        "menu-item":          "/static/ui_components/js/components/menu-item.js",
        "collapse-button":    "/static/ui_components/js/components/collapse-button.js",
        "hamburger-button":   "/static/ui_components/js/components/hamburger-button.js",
        "notification-panel": "/static/ui_components/js/components/notification-panel.js",
        "user-menu":          "/static/ui_components/js/components/user-menu.js",
        "search":             "/static/ui_components/js/components/search.js",
        "sidebar":            "/static/ui_components/js/components/sidebar.js",
        "content-container":  "/static/ui_components/js/components/content-container.js",
        "coin-watchlist":     "/static/ui_components/js/components/coin-watchlist.js",
        "progress-bar":       "/static/ui_components/js/components/progress-bar.js",
    }

    # Public URL of the combined bundle. Loads every component at once.
    BUNDLE_URL = "/static/ui_components/js/main.js"

    def __init__(self, logger=None):
        self.logger = logger
        self._components = dict(self.DEFAULT_COMPONENTS)

    # --------------------------------------------------------------
    # Public API
    # --------------------------------------------------------------
    def register_component(self, name, url):
        """
        Register a new component or override an existing one.

        Parameters
        ----------
        name : str
            Logical name (e.g. "card").
        url : str
            Public URL to the component's JS file.
        """
        if not name or not url:
            return False
        self._components[name] = url
        if self.logger:
            self.logger.log(
                f"Registered component '{name}' → {url}",
                tag="ui"
            )
        return True

    def unregister_component(self, name):
        """Remove a component from the registry. Returns True if found."""
        if name in self._components:
            del self._components[name]
            if self.logger:
                self.logger.log(f"Unregistered component '{name}'", tag="ui")
            return True
        return False

    def is_registered(self, name):
        """Check whether a component name is registered."""
        return name in self._components

    def get_component_url(self, name):
        """Return the public URL of a component, or None if not found."""
        return self._components.get(name)

    def get_component_urls(self, names):
        """
        Return a list of URLs for the given names, skipping any that
        are not registered. Duplicates are removed while preserving
        the input order.
        """
        seen = set()
        result = []
        for name in names:
            url = self._components.get(name)
            if url and url not in seen:
                seen.add(url)
                result.append(url)
        return result

    def get_all_components(self):
        """Return a copy of the registry (name → url)."""
        return dict(self._components)

    def get_component_paths(self):
        """Return a list of all registered component URLs."""
        return list(self._components.values())

    def get_bundle_url(self):
        """Return the URL of the bundle entry point (loads everything)."""
        return self.BUNDLE_URL
