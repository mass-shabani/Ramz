import { defineComponent, attr } from '../_base.js';

/**
 * <ramz-topbar>
 *
 * A reusable topbar for standalone pages (profile, account settings, ...).
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
 *
 * Slots:
 *   • actions  — content placed on the right, before the user menu
 *   • center   — optional center content (search bar, tabs, ...)
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
    // Only re-render if we're updating brand/user attributes
    this.#build();
  }

  /* --------------------------------------------------------------
     Capture children before we overwrite innerHTML
     -------------------------------------------------------------- */
  #capture() {
    if (this.#captured) return;
    const children = Array.from(this.children);
    this.#captured = {
      actions: children.filter(el => el.getAttribute('slot') === 'actions'),
      center:  children.filter(el => el.getAttribute('slot') === 'center'),
    };
  }

  #reapplyCaptured() {
    // If the caller appended children after we already built the tree,
    // move them into the correct slot wrapper.
    const actionsWrap = this.querySelector('.standalone-actions');
    const centerWrap  = this.querySelector('.standalone-center');
    if (!actionsWrap) return;

    Array.from(this.children).forEach(child => {
      if (child.classList.contains('standalone-topbar-inner')) return;
      const slot = child.getAttribute('slot');
      if (slot === 'actions' && actionsWrap) {
        actionsWrap.insertBefore(child, actionsWrap.lastElementChild);
      } else if (slot === 'center' && centerWrap) {
        centerWrap.appendChild(child);
      }
    });
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

    /* --- Brand (link wrapper + ramz-brand inside) --- */
    const brandLink = document.createElement('a');
    brandLink.className = 'standalone-brand';
    brandLink.href = brandHref;

    const brand = document.createElement('ramz-brand');
    brand.setAttribute('name', brandName);
    brand.setAttribute('subtitle', brandSub);
    brandLink.appendChild(brand);
    header.appendChild(brandLink);

    /* --- Center slot (only if content was provided) --- */
    const hasCenter = this.#captured.center && this.#captured.center.length > 0;
    if (hasCenter) {
      const centerWrap = document.createElement('div');
      centerWrap.className = 'standalone-center';
      this.#captured.center.forEach(el => centerWrap.appendChild(el));
      header.appendChild(centerWrap);
    }

    /* --- Actions + user menu --- */
    const actionsWrap = document.createElement('div');
    actionsWrap.className = 'standalone-actions';

    if (this.#captured.actions) {
      this.#captured.actions.forEach(el => actionsWrap.appendChild(el));
    }

    const userMenu = document.createElement('ramz-user-menu');
    userMenu.setAttribute('user-name', userName);
    userMenu.setAttribute('user-email', userEmail);
    userMenu.setAttribute('user-initials', userInitials);
    actionsWrap.appendChild(userMenu);

    header.appendChild(actionsWrap);
    this.appendChild(header);

    this.#built = true;
  }
}

defineComponent('ramz-topbar', RamzTopbar);
