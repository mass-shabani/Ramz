import { defineComponent, emit } from '../_base.js';

/**
 * <ramz-sidebar>
 *
 * Manages the desktop collapse state and the mobile drawer of the
 * sidebar. The component does not build any internal structure — all
 * markup (brand, nav, promo, footer) comes from `panel_layout.html`.
 *
 * The sidebar listens to events emitted by its descendants:
 *   • ramz:sidebar-toggle — from <ramz-collapse-btn>, toggles state
 *   • ramz:load-content   — from <ramz-menu-item>, closes the mobile drawer
 *
 * Public API:
 *   • open()         — open the mobile drawer
 *   • close()        — close the mobile drawer
 *   • toggle()       — toggle collapsed (desktop) or drawer (mobile)
 *   • isCollapsed()  — read-only state check
 *   • collapse()     — force collapsed state (desktop)
 *   • expand()       — force expanded state (desktop)
 */
class RamzSidebar extends HTMLElement {
  #collapsed   = false;
  #mobileOpen  = false;
  #bound       = false;

  connectedCallback() {
    // Ensure the .sidebar class is present so global CSS applies
    this.classList.add('sidebar');
    if (!this.id) this.id = 'sidebar';

    if (this.#bound) return;
    this.#bound = true;

    this.addEventListener('ramz:sidebar-toggle', this._onToggleRequest);
    this.addEventListener('ramz:load-content',    this._onLoadContent);
    window.addEventListener('resize',             this._onResize);

    // Append extension-provided items into the sidebar nav.
    this._renderExtensions();
  }

  disconnectedCallback() {
    this.removeEventListener('ramz:sidebar-toggle', this._onToggleRequest);
    this.removeEventListener('ramz:load-content',    this._onLoadContent);
    window.removeEventListener('resize',             this._onResize);

    // Safety: restore body scroll if we were open on mobile
    if (this.#mobileOpen) {
      document.body.classList.remove('no-scroll');
      document.getElementById('overlay')?.classList.remove('show');
    }
  }

  /* --------------------------------------------------------------
     Public API
     -------------------------------------------------------------- */
  open() {
    // No-op on desktop widths — the mobile drawer is not used there
    if (window.innerWidth >= 1024) return;
    if (this.#mobileOpen) return;

    this.#mobileOpen = true;
    this.classList.add('mobile-open');
    document.getElementById('overlay')?.classList.add('show');
    document.body.classList.add('no-scroll');
  }

  close() {
    if (!this.#mobileOpen) return;

    this.#mobileOpen = false;
    this.classList.remove('mobile-open');
    document.getElementById('overlay')?.classList.remove('show');
    document.body.classList.remove('no-scroll');
  }

  toggle() {
    if (window.innerWidth >= 1024) {
      this._toggleCollapsed();
    } else {
      this.#mobileOpen ? this.close() : this.open();
    }
  }

  isCollapsed() {
    return this.#collapsed;
  }

  collapse() {
    if (this.#collapsed) return;
    this.#collapsed = true;
    this._applyCollapsed();
  }

  expand() {
    if (!this.#collapsed) return;
    this.#collapsed = false;
    this._applyCollapsed();
  }

  /* --------------------------------------------------------------
     Internal
     -------------------------------------------------------------- */
  _toggleCollapsed() {
    this.#collapsed = !this.#collapsed;
    this._applyCollapsed();
  }

  _applyCollapsed() {
    this.classList.toggle('collapsed', this.#collapsed);

    // Reflect to the collapse button so it can swap its label
    const btn = this.querySelector('ramz-collapse-btn');
    if (btn) {
      if (this.#collapsed) btn.setAttribute('collapsed', '');
      else                 btn.removeAttribute('collapsed');
    }
  }

  /* --------------------------------------------------------------
     Extensions
     -------------------------------------------------------------- */

  /**
   * Read `window.__ramz.extensions['ui.sidebar.items']` and append
   * each entry to the sidebar <nav>. Entries with a `group` label
   * are placed inside a <ramz-menu-group> (existing group with the
   * same label is reused, otherwise a new one is created at the end
   * of the nav). Entries without a group are appended directly to
   * the nav.
   *
   * The list is already sorted by `order` server-side, so this method
   * preserves the incoming order.
   */
  _renderExtensions() {
    const extensions = (window.__ramz && window.__ramz.extensions)
      ? window.__ramz.extensions['ui.sidebar.items']
      : null;
    if (!Array.isArray(extensions) || extensions.length === 0) return;

    const nav = this.querySelector('nav.nav');
    if (!nav) return;

    // Track newly-created groups so subsequent items in the same
    // group land in the same element without duplicating wrappers.
    const newGroups = new Map();

    for (const item of extensions) {
      const menuItem = this._buildExtensionMenuItem(item);
      if (!menuItem) continue;

      const groupLabel = item.group;

      if (groupLabel) {
        let groupEl = null;
        for (const g of nav.querySelectorAll('ramz-menu-group')) {
          if (g.getAttribute('label') === groupLabel) {
            groupEl = g;
            break;
          }
        }
        if (!groupEl && newGroups.has(groupLabel)) {
          groupEl = newGroups.get(groupLabel);
        }
        if (!groupEl) {
          groupEl = document.createElement('ramz-menu-group');
          groupEl.setAttribute('label', groupLabel);
          nav.appendChild(groupEl);
          newGroups.set(groupLabel, groupEl);
        }
        groupEl.appendChild(menuItem);
      } else {
        nav.appendChild(menuItem);
      }
    }
  }

  /**
   * Build a <ramz-menu-item> from an extension entry.
   * Returns null when the entry is missing a `label`.
   */
  _buildExtensionMenuItem(item) {
    if (!item || !item.label) return null;

    const el = document.createElement('ramz-menu-item');
    el.setAttribute('label', item.label);
    if (item.endpoint) el.setAttribute('endpoint', item.endpoint);
    if (item.href)     el.setAttribute('href',     item.href);
    if (item.icon) {
      const iconSlot = document.createElement('span');
      iconSlot.setAttribute('slot', 'icon');
      iconSlot.innerHTML = item.icon;
      el.appendChild(iconSlot);
    }
    return el;
  }

  /* --------------------------------------------------------------
     Event handlers
     -------------------------------------------------------------- */
  _onToggleRequest = (e) => {
    // Only respond to events originating inside this sidebar
    if (!this.contains(e.target)) return;
    this.toggle();
  };

  _onLoadContent = (e) => {
    // Close the mobile drawer when a menu item triggers a content load
    if (!this.contains(e.target)) return;
    if (this.#mobileOpen) this.close();
  };

  _onResize = () => {
    // Crossing into desktop: the mobile drawer is no longer relevant
    if (window.innerWidth >= 1024 && this.#mobileOpen) {
      this.close();
    }
  };
}

defineComponent('ramz-sidebar', RamzSidebar);