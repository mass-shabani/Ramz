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