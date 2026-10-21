import { defineComponent, attr } from '../_base.js';

/**
 * <ramz-topbar>
 *
 * A reusable topbar for standalone pages (profile, account settings, admin).
 *
 * Structure:
 *   ┌──────────────────────────────────────────────────┐
 *   │  [brand]          [center slot]      [actions] │ [user-menu] │
 *   └──────────────────────────────────────────────────┘
 *
 * Attributes:
 *   • user-name       — pass-through to ramz-user-menu
 *   • user-email      — pass-through to ramz-user-menu
 *   • user-initials   — pass-through to ramz-user-menu
 *   • brand-name      — pass-through to ramz-brand (default: "Nebula")
 *   • brand-subtitle  — pass-through to ramz-brand (default: "Admin Suite")
 *   • brand-href      — link for the brand block (default: "/panel")
 *   • show-progress   — if present, render a ramz-progress-bar inside
 *
 * Slots (Light DOM — captured and re-inserted manually):
 *   • hamburger  — content placed before the brand (mobile trigger)
 *   • start      — content placed left, after brand
 *   • center     — content placed in the center
 *
 * Topbar actions:
 *   Buttons/links are read from window.__ramz.extensions["ui.topbar.actions"].
 *   Each item is either:
 *     { href, title, aria_label, icon, order? }   — structural mode
 *   or:
 *     { html, order? }                            — raw HTML escape hatch
 *
 *   Extensions render inside the actions wrap, before the user menu.
 *   The legacy slot="actions" mechanism has been REMOVED — all topbar
 *   actions must go through the extension registry.
 *
 * The component builds its own inner tree on connectedCallback and
 * manually re-attaches the user-provided slot content. This is
 * necessary because `<slot>` does not work in Light DOM.
 */
class RamzTopbar extends HTMLElement {
  static get observedAttributes() {
    return [
      'user-name', 'user-email', 'user-initials',
      'brand-name', 'brand-subtitle', 'brand-href',
      'show-progress',
    ];
  }

  #captured = null;
  #built    = false;

  connectedCallback() {
    if (this.#built) return;

    this.#capture();
    this.#build();

    queueMicrotask(() => {
      // Re-capture after any children appended immediately after
      // appendChild() are in place.
      if (!this.#built) return;
      this.#reapplyCaptured();
    });
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal) return;
    if (!this.#built) return;
    this.#build();
  }

  /* --------------------------------------------------------------
     Capture children before we overwrite innerHTML
     -------------------------------------------------------------- */
  #capture() {
    if (this.#captured) return;
    const children = Array.from(this.children);
    this.#captured = {
      hamburger: children.filter(el => el.getAttribute('slot') === 'hamburger'),
      start:     children.filter(el => el.getAttribute('slot') === 'start'),
      center:    children.filter(el => el.getAttribute('slot') === 'center'),
    };
  }

  #reapplyCaptured() {
    // If the caller appended children after we already built the tree,
    // move them into the correct slot wrapper.
    const hamburgerWrap = this.querySelector('.standalone-hamburger');
    const startWrap     = this.querySelector('.standalone-start');
    const centerWrap    = this.querySelector('.standalone-center');
    if (!hamburgerWrap && !startWrap && !centerWrap) return;

    Array.from(this.children).forEach(child => {
      if (child.classList.contains('standalone-topbar-inner')) return;
      const slot = child.getAttribute('slot');
      if (slot === 'hamburger' && hamburgerWrap) {
        hamburgerWrap.appendChild(child);
      } else if (slot === 'start' && startWrap) {
        startWrap.appendChild(child);
      } else if (slot === 'center' && centerWrap) {
        centerWrap.appendChild(child);
      }
    });
  }

  /* --------------------------------------------------------------
     Extension helpers
     -------------------------------------------------------------- */
  #getActionExtensions() {
    const ext = window.__ramz && window.__ramz.extensions;
    if (!ext) return [];
    const items = ext['ui.topbar.actions'];
    return Array.isArray(items) ? items : [];
  }

  #renderActionItem(item) {
    // Raw HTML escape hatch
    if (item.html) {
      const template = document.createElement('template');
      template.innerHTML = String(item.html).trim();
      return template.content.firstElementChild;
    }

    // Structural mode: render as a standard icon-btn anchor
    const a = document.createElement('a');
    a.className = 'icon-btn';
    a.href = item.href || '#';
    a.title = item.title || '';
    a.setAttribute('aria-label', item.aria_label || item.title || '');

    const icon = item.icon;
    if (icon) {
      const trimmed = String(icon).trim();
      if (trimmed.startsWith('<')) {
        a.innerHTML = trimmed;
      } else {
        a.textContent = trimmed;
      }
    }

    return a;
  }

  /* --------------------------------------------------------------
     Build the inner tree
     -------------------------------------------------------------- */
  #build() {
    this.#capture();

    const userName     = attr(this, 'user-name', '');
    const userEmail    = attr(this, 'user-email', '');
    const userInitials = attr(this, 'user-initials', '');
    const brandName    = attr(this, 'brand-name', 'Nebula');
    const brandSub     = attr(this, 'brand-subtitle', 'Admin Suite');
    const brandHref    = attr(this, 'brand-href', '/panel');

    this.innerHTML = '';

    /* --- Header --- */
    const header = document.createElement('header');
    header.className = 'standalone-topbar standalone-topbar-inner';

    /* --- Hamburger slot (before brand, mobile only) --- */
    const hasHamburger = this.#captured.hamburger && this.#captured.hamburger.length > 0;
    if (hasHamburger) {
      const hamburgerWrap = document.createElement('div');
      hamburgerWrap.className = 'standalone-hamburger';
      this.#captured.hamburger.forEach(el => hamburgerWrap.appendChild(el));
      header.appendChild(hamburgerWrap);
    }

    /* --- Brand (link wrapper + ramz-brand inside) --- */
    const brandLink = document.createElement('a');
    brandLink.className = 'standalone-brand';
    brandLink.href = brandHref;

    const brand = document.createElement('ramz-brand');
    brand.setAttribute('name', brandName);
    brand.setAttribute('subtitle', brandSub);
    brandLink.appendChild(brand);
    header.appendChild(brandLink);

    /* --- Start slot (left side, after brand) --- */
    const hasStart = this.#captured.start && this.#captured.start.length > 0;
    if (hasStart) {
      const startWrap = document.createElement('div');
      startWrap.className = 'standalone-start';
      this.#captured.start.forEach(el => startWrap.appendChild(el));
      header.appendChild(startWrap);
    }

    /* --- Center slot (only if content was provided) --- */
    const hasCenter = this.#captured.center && this.#captured.center.length > 0;
    if (hasCenter) {
      const centerWrap = document.createElement('div');
      centerWrap.className = 'standalone-center';
      this.#captured.center.forEach(el => centerWrap.appendChild(el));
      header.appendChild(centerWrap);
    }

    /* --- Actions + extensions + user menu --- */
    const actionsWrap = document.createElement('div');
    actionsWrap.className = 'standalone-actions';

    // Extensions first (before the user menu)
    const extensions = this.#getActionExtensions();
    extensions.forEach(item => {
      const el = this.#renderActionItem(item);
      if (el) actionsWrap.appendChild(el);
    });

    // User menu always last
    const userMenu = document.createElement('ramz-user-menu');
    userMenu.setAttribute('user-name', userName);
    userMenu.setAttribute('user-email', userEmail);
    userMenu.setAttribute('user-initials', userInitials);
    actionsWrap.appendChild(userMenu);

    header.appendChild(actionsWrap);

    /* --- Optional progress bar (for AJAX loading feedback) --- */
    const showProgress = this.hasAttribute('show-progress');
    if (showProgress) {
      const progress = document.createElement('ramz-progress-bar');
      header.appendChild(progress);
    }

    this.appendChild(header);

    this.#built = true;
  }
}

defineComponent('ramz-topbar', RamzTopbar);
