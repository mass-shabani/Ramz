import { defineComponent, attr, emit } from '../_base.js';

/**
 * <ramz-user-menu>
 *
 * User chip + dropdown menu.
 *
 * Attributes:
 *   • user-name     — display name (default: "User")
 *   • user-email    — email address
 *   • user-initials — avatar initials (default: derived from name)
 *   • logout-url    — logout link target (default: "/logout")
 *
 * Extension source:
 *   Extra menu items are read from window.__ramz.extensions["ui.user_menu.items"].
 *   Each item is either:
 *     { label, url, icon?, order? }   — structural mode
 *   or:
 *     { html, order? }                — raw HTML escape hatch
 *
 * Public API:
 *   • open()   — open the dropdown
 *   • close()  — close the dropdown
 *   • toggle() — toggle the dropdown
 */
class RamzUserMenu extends HTMLElement {
  static get observedAttributes() {
    return [
      'user-name',
      'user-email',
      'user-initials',
      'logout-url',
    ];
  }

  #open = false;
  #refs = {};

  connectedCallback() {
    this._render();
    this._cacheRefs();
    this._attachListeners();
    window.addEventListener('ramz:user-updated', this._onUserUpdated);
  }

  disconnectedCallback() {
    this._detachListeners();
    window.removeEventListener('ramz:user-updated', this._onUserUpdated);
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal) return;
    if (!this.isConnected) return;
    this._render();
    this._cacheRefs();
  }

  /* --------------------------------------------------------------
     Public API
     -------------------------------------------------------------- */
  open() {
    if (this.#open) return;
    this.#open = true;
    this._sync();
    emit(this, 'ramz:close-dropdowns', { except: 'user-menu' });
  }

  close() {
    if (!this.#open) return;
    this.#open = false;
    this._sync();
  }

  toggle() {
    this.#open ? this.close() : this.open();
  }

  /* --------------------------------------------------------------
     Helpers
     -------------------------------------------------------------- */
  _data() {
    const name = attr(this, 'user-name', 'User');
    const email = attr(this, 'user-email', '');
    const initials = attr(this, 'user-initials', '') ||
      (name.trim().split(/\s+/).map(p => p[0]).slice(0, 2).join('').toUpperCase() || 'U');
    const logoutUrl = attr(this, 'logout-url', '/logout');

    return { name, email, initials, logoutUrl };
  }

  /* --------------------------------------------------------------
     Rendering
     -------------------------------------------------------------- */
  _render() {
    const { name, email, initials, logoutUrl } = this._data();

    this.innerHTML = `
      <div class="dropdown-wrap">
        <button class="user-chip" type="button"
                aria-haspopup="true"
                aria-expanded="false">
          <span class="avatar avatar--indigo">${initials}</span>
          <span class="user-name">${name}</span>
          <svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m6 9 6 6 6-6"/>
          </svg>
        </button>

        <div class="dropdown user-menu" role="menu">
          <div class="um-head">
            <span class="avatar avatar--indigo">${initials}</span>
            <div class="um-info">
              <div class="um-name">${name}</div>
              <div class="um-mail">${email}</div>
            </div>
          </div>

          <a class="um-item" href="/profile">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="8" r="3.6"/>
              <path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>
            </svg>
            My Profile
          </a>

          <a class="um-item" href="/settings/account">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7.9 19.4l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 4 13.9H4a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 5.3 7.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 10.9 4V4a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0 1.1 2.7H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1.3z"/>
            </svg>
            Account Settings
            <span class="kbd">⌘,</span>
          </a>

          ${this._renderExtraLinks()}

          <a class="um-item" href="#">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="5" width="20" height="14" rx="3"/>
              <path d="M2 10h20"/>
            </svg>
            Billing &amp; Plans
          </a>

          <a class="um-item" href="#">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="9"/>
              <path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.3"/>
              <path d="M12 17h.01"/>
            </svg>
            Help &amp; Support
          </a>

          <div class="um-divider"></div>

          <a class="um-item logout" href="${logoutUrl}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 21H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3"/>
              <path d="M16 17l5-5-5-5"/>
              <path d="M21 12H9"/>
            </svg>
            Log Out
          </a>
        </div>
      </div>
    `;
  }

  /* --------------------------------------------------------------
     Extension links (from window.__ramz.extensions)
     -------------------------------------------------------------- */
  _getExtraLinks() {
    const ext = window.__ramz && window.__ramz.extensions;
    if (!ext) return [];
    const items = ext['ui.user_menu.items'];
    return Array.isArray(items) ? items : [];
  }

  _renderExtraLinks() {
    const links = this._getExtraLinks();
    if (!links.length) return '';

    return links.map(link => {
      if (link.html) return link.html;

      const url   = this._escapeAttr(link.url || '#');
      const label = this._escapeHtml(link.label || '');
      const icon  = this._renderFeatureIcon(link.icon);

      return `
        <a class="um-item" href="${url}">
          ${icon}
          ${label}
        </a>
      `;
    }).join('');
  }

  _renderFeatureIcon(icon) {
    if (!icon) {
      return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="1.9" stroke-linecap="round"
                   stroke-linejoin="round">
                <path d="M12 2 4 6v6c0 5 3.4 9.4 8 10 4.6-.6 8-5 8-10V6z"/>
              </svg>`;
    }
    const trimmed = String(icon).trim();
    if (trimmed.startsWith('<')) {
      return trimmed;
    }
    return `<span style="font-size: 16px; line-height: 1;">${this._escapeHtml(trimmed)}</span>`;
  }

  _escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  _escapeAttr(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  _cacheRefs() {
    const root = this.querySelector('.dropdown-wrap');
    this.#refs = {
      root,
      trigger: root.querySelector('.user-chip'),
      panel:   root.querySelector('.dropdown')
    };
  }

  _sync() {
    const { root, panel, trigger } = this.#refs;
    root.classList.toggle('active', this.#open);
    panel.classList.toggle('open', this.#open);
    trigger.setAttribute('aria-expanded', String(this.#open));
  }

  /* --------------------------------------------------------------
     Listeners
     -------------------------------------------------------------- */
  _attachListeners() {
    this.addEventListener('click', this._onClick);
    document.addEventListener('click', this._onDocumentClick);
    window.addEventListener('ramz:close-dropdowns', this._onGlobalClose);
  }

  _detachListeners() {
    this.removeEventListener('click', this._onClick);
    document.removeEventListener('click', this._onDocumentClick);
    window.removeEventListener('ramz:close-dropdowns', this._onGlobalClose);
  }

  _onClick = (e) => {
    const trigger = e.target.closest('.user-chip');
    if (trigger && this.contains(trigger)) {
      e.stopPropagation();
      this.toggle();
    }
  };

  _onDocumentClick = (e) => {
    if (!this.contains(e.target)) this.close();
  };

  _onGlobalClose = (e) => {
    if (e.detail?.except !== 'user-menu') this.close();
  };

  /* --------------------------------------------------------------
     Public API — live update from external source
     -------------------------------------------------------------- */
  setUser({ name, email, initials } = {}) {
    if (name !== undefined)     this.setAttribute('user-name', name || '');
    if (email !== undefined)    this.setAttribute('user-email', email || '');
    if (initials !== undefined) this.setAttribute('user-initials', initials || '');
    // attributeChangedCallback → _render() → DOM updated
  }

  _onUserUpdated = (e) => {
    const data = e.detail || {};
    this.setUser(data);
  };
}

defineComponent('ramz-user-menu', RamzUserMenu);
