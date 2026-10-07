import { LitElement, html, css } from '../lit-import.js';

export class NebulaUserMenu extends LitElement {
  static properties = {
    userName:     { type: String },
    userEmail:    { type: String },
    userInitials: { type: String },
    _open:        { state: true }
  };

  constructor() {
    super();
    this.userName = 'User';
    this.userEmail = '';
    this.userInitials = 'U';
    this._open = false;
  }

  createRenderRoot() { return this; }

  /* static styles commented out — managed globally in style.css */
  /* static styles = css`
    :host { display: block; }

    .dropdown-wrap { position: relative; }

    .user-chip {
      display: flex;
      align-items: center;
      gap: 10px;
      height: 44px;
      padding: 0 12px 0 6px;
      border-radius: 13px;
      cursor: pointer;
      color: var(--text);
      background: rgba(30, 41, 66, 0.6);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      transition: background .18s, border-color .18s;
    }

    .user-chip:hover {
      background: rgba(40, 54, 84, 0.85);
      border-color: rgba(129,140,248,.45);
    }

    .user-chip .avatar {
      position: relative;
    }

    .user-chip .avatar::after {
      content: '';
      position: absolute;
      right: -2px;
      bottom: -2px;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--success);
      border: 2px solid #1a2540;
    }

    .user-name { font-size: 13px; font-weight: 600; white-space: nowrap; }

    .user-chip .chev {
      width: 15px;
      height: 15px;
      color: var(--muted);
      transition: transform .28s;
    }

    .dropdown-wrap.active .user-chip .chev { transform: rotate(180deg); }
    .dropdown-wrap.active .user-chip {
      background: rgba(48, 63, 96, 0.9);
      border-color: rgba(129,140,248,.55);
    }

    .dropdown {
      position: absolute;
      top: calc(100% + 12px);
      right: 0;
      z-index: 60;
      border-radius: 18px;
      opacity: 0;
      visibility: hidden;
      transform: translateY(-10px) scale(.97);
      transform-origin: top right;
      transition: opacity .22s ease, transform .22s cubic-bezier(.34,1.3,.64,1), visibility .22s;
    }

    .dropdown.open {
      opacity: 1;
      visibility: visible;
      transform: translateY(0) scale(1);
    }

    .user-menu {
      width: min(260px, calc(100vw - 28px));
      padding: 10px;
      background: linear-gradient(180deg, rgba(58, 74, 112, 0.98) 0%, rgba(42, 56, 88, 0.98) 100%);
      backdrop-filter: blur(26px) saturate(160%);
      -webkit-backdrop-filter: blur(26px) saturate(160%);
      border: 1px solid rgba(129, 140, 248, 0.35);
      box-shadow:
        0 28px 70px -18px rgba(0, 0, 0, 0.95),
        0 0 0 1px rgba(129, 140, 248, 0.12),
        0 0 40px -10px rgba(99, 102, 241, 0.35),
        inset 0 1px 0 rgba(255, 255, 255, 0.12);
    }

    .user-menu::before {
      content: '';
      position: absolute;
      top: -6px;
      right: 26px;
      width: 12px;
      height: 12px;
      background: rgba(58, 74, 112, 0.98);
      border-left: 1px solid rgba(129, 140, 248, 0.35);
      border-top: 1px solid rgba(129, 140, 248, 0.35);
      transform: rotate(45deg);
      border-radius: 2px 0 0 0;
    }

    .um-head {
      display: flex;
      align-items: center;
      gap: 11px;
      padding: 12px 10px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.09);
      margin-bottom: 8px;
    }

    .um-head .avatar {
      width: 42px;
      height: 42px;
      border-radius: 13px;
      font-size: 14px;
    }

    .um-info { min-width: 0; }

    .um-name {
      font-size: 14px;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .um-mail {
      font-size: 11.5px;
      color: #b9c4dc;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-top: 2px;
    }

    .um-item {
      display: flex;
      align-items: center;
      gap: 11px;
      height: 42px;
      padding: 0 11px;
      border-radius: 11px;
      font-size: 13px;
      font-weight: 500;
      color: #dde5f4;
      text-decoration: none;
      transition: background .16s, color .16s;
    }

    .um-item:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }

    .um-item svg {
      width: 17px;
      height: 17px;
      flex: 0 0 auto;
      color: #a5b4fc;
    }

    .um-item:hover svg { color: #c7d2fe; }

    .um-item .kbd {
      margin-left: auto;
      font-size: 10px;
      font-weight: 600;
      color: #b9c4dc;
      background: rgba(255, 255, 255, 0.07);
      border: 1px solid rgba(255, 255, 255, 0.08);
      padding: 2px 6px;
      border-radius: 5px;
    }

    .um-divider {
      height: 1px;
      background: rgba(255, 255, 255, 0.09);
      margin: 8px 4px;
    }

    .um-item.logout { color: #fb7185; }
    .um-item.logout svg { color: #fb7185; }
    .um-item.logout:hover {
      background: rgba(244, 63, 94, 0.16);
      color: #fecdd3;
    }
    .um-item.logout:hover svg { color: #fecdd3; }
  `; */

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
               <path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1.5-1.3l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 2.7-1.1V14a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1.5 1.3l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21"/>
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
