import { defineComponent, attr, emit } from '../_base.js';

/**
 * <ramz-menu-item>
 *
 * A single sidebar navigation item. Supports an arbitrary element as
 * its icon via `slot="icon"` (svg, img, div, button, etc.).
 *
 * Attributes:
 *   • label          — visible text
 *   • href           — anchor target (defaults to "#")
 *   • endpoint       — URL to POST when clicked (triggers content load)
 *   • badge          — optional badge text
 *   • badge-variant  — "" | "danger"
 *   • active         — marks the item as active
 *   • tooltip        — title attribute (falls back to label)
 *
 * Slot:
 *   • icon  — any single element that represents the icon
 *
 * Emits:
 *   • ramz:load-content  — { url, label } when the item has an endpoint
 *
 * Public API:
 *   • activate()
 *   • deactivate()
 */
class RamzMenuItem extends HTMLElement {
  static get observedAttributes() {
    return ['label', 'href', 'endpoint', 'badge', 'badge-variant', 'active', 'tooltip'];
  }

  #captured = null;
  #built    = false;
  #refs     = {};

  /* --------------------------------------------------------------
     Lifecycle
     -------------------------------------------------------------- */
  connectedCallback() {
    if (this.#built) return;

    // Capture the icon slot children once, before we ever touch innerHTML
    this.#captured = {
      icon: Array.from(this.children)
        .filter(el => el.getAttribute('slot') === 'icon')
    };

    // Defer build by one microtask so that children appended right
    // after appendChild() are captured as well.
    queueMicrotask(() => {
      if (this.#built) return;
      this.#built = true;
      this._build();
    });

    this.addEventListener('click', this._onClick);
  }

  disconnectedCallback() {
    this.removeEventListener('click', this._onClick);
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal) return;
    if (!this.#built) return;

    // Active is a soft change — just toggle the class
    if (name === 'active') {
      this._syncActive();
      return;
    }

    // Structural attributes require a rebuild
    this._build();
  }

  /* --------------------------------------------------------------
     Public API
     -------------------------------------------------------------- */
  activate() {
    this.setAttribute('active', '');
  }

  deactivate() {
    this.removeAttribute('active');
  }

  /* --------------------------------------------------------------
     Build
     -------------------------------------------------------------- */
  _build() {
    const label        = attr(this, 'label', '');
    const href         = attr(this, 'href', '#');
    const badge        = attr(this, 'badge', '');
    const badgeVariant = attr(this, 'badge-variant', '');
    const tooltip      = attr(this, 'tooltip', label);
    const isActive     = this.hasAttribute('active');

    /* Preserve focus state — but only if this component owns the focus */
    const hadFocus = document.activeElement && this.contains(document.activeElement);

    this.innerHTML = '';

    const link = document.createElement('a');
    link.className = 'nav-item' + (isActive ? ' active' : '');
    link.href = href;
    link.title = tooltip;

    /* --- Icon --- */
    const iconWrap = document.createElement('span');
    iconWrap.className = 'nav-icon';
    this.#captured.icon.forEach(el => iconWrap.appendChild(el));
    link.appendChild(iconWrap);

    /* --- Label --- */
    const text = document.createElement('span');
    text.className = 'nav-text';
    text.textContent = label;
    link.appendChild(text);

    /* --- Badge --- */
    if (badge) {
      const badgeEl = document.createElement('span');
      badgeEl.className = 'nav-badge' + (badgeVariant === 'danger' ? ' danger' : '');
      badgeEl.textContent = badge;
      link.appendChild(badgeEl);
    }

    this.appendChild(link);
    this.#refs.link = link;

    if (hadFocus) link.focus();
  }

  _syncActive() {
    const link = this.#refs.link;
    if (!link) return;
    link.classList.toggle('active', this.hasAttribute('active'));
  }

  /* --------------------------------------------------------------
     Click handling
     -------------------------------------------------------------- */
  _onClick = (e) => {
    const link = e.target.closest('.nav-item');
    if (!link || !this.contains(link)) return;

    const endpoint = this.getAttribute('endpoint');
    if (!endpoint) return;   // No endpoint → allow default navigation

    e.preventDefault();
    this._activateSelf();

    emit(this, 'ramz:load-content', {
      url: endpoint,
      label: this.getAttribute('label') || ''
    });
  };

  _activateSelf() {
    // Deactivate every sibling item inside the same sidebar
    const sidebar = this.closest('ramz-sidebar') || document;
    sidebar.querySelectorAll('ramz-menu-item').forEach(item => {
      if (item !== this) item.deactivate();
    });

    this.activate();
  }
}

defineComponent('ramz-menu-item', RamzMenuItem);