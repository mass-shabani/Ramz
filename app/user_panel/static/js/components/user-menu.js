import { LitElement, html } from '../lit-import.js';

export class NebulaUserMenu extends LitElement {
  static properties = {
    userName:     { type: String },
    userEmail:    { type: String },
    userInitials: { type: String },
    _open:        { state: true }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.userName = 'User';
    this.userEmail = '';
    this.userInitials = 'U';
    this._open = false;
  }

  connectedCallback() {
    super.connectedCallback();
    document.addEventListener('click', this._onDocClick);
    window.addEventListener('nebula:close-dropdowns', this._onGlobalClose);
  }

  disconnectedCallback() {
    document.removeEventListener('click', this._onDocClick);
    window.removeEventListener('nebula:close-dropdowns', this._onGlobalClose);
    super.disconnectedCallback();
  }

  _onDocClick = (e) => { if (!this.contains(e.target)) this._open = false; };
  _onGlobalClose = (e) => { if (e.detail?.except !== 'user-menu') this._open = false; };

  _toggle(e) {
    e.stopPropagation();
    this._open = !this._open;
    if (this._open) {
      window.dispatchEvent(new CustomEvent('nebula:close-dropdowns', {
        detail: { except: 'user-menu' }
      }));
    }
  }

  close() { this._open = false; }

  render() {
    return html`
      <div class="dropdown-wrap ${this._open ? 'active' : ''}">
        <button class="user-chip" type="button"
                aria-haspopup="true" aria-expanded="${this._open}"
                @click=${this._toggle}>
          <span class="avatar avatar--indigo">${this.userInitials}</span>
          <span class="user-name">${this.userName}</span>
          <svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m6 9 6 6 6-6"/>
          </svg>
        </button>

        <div class="dropdown user-menu ${this._open ? 'open' : ''}" role="menu">
          <div class="um-head">
            <span class="avatar avatar--indigo">${this.userInitials}</span>
            <div class="um-info">
              <div class="um-name">${this.userName}</div>
              <div class="um-mail">${this.userEmail}</div>
            </div>
          </div>

          <a class="um-item" href="#">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="8" r="3.6"/>
              <path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>
            </svg>
            My Profile
          </a>

          <a class="um-item" href="#">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7.9 19.4l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 4 13.9H4a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 5.3 7.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 10.9 4V4a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0 1.1 2.7H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1.3z"/>
            </svg>
            Account Settings
            <span class="kbd">⌘,</span>
          </a>

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

          <a class="um-item logout" href="/logout">
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
}

customElements.define('nebula-user-menu', NebulaUserMenu);