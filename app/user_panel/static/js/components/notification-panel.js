import { LitElement, html } from '../lit-import.js';

const DEFAULT_NOTIFICATIONS = [
  { unread: true,  title: 'BTC prediction updated',   text: '72% bullish confidence.',           time: '2 minutes ago',  iconClass: 'icon-soft--indigo', icon: 'chat' },
  { unread: true,  title: 'ETH crossed target',       text: 'Crossed your target of $3,200.',   time: '18 minutes ago', iconClass: 'icon-soft--green',  icon: 'trend' },
  { unread: true,  title: 'Volatility detected',      text: 'Unusual volatility on SOL/USDT.',  time: '1 hour ago',     iconClass: 'icon-soft--amber',  icon: 'alert' },
  { unread: true,  title: 'Weekly AI report ready',   text: '+18.4% signal accuracy.',          time: '3 hours ago',    iconClass: 'icon-soft--rose',   icon: 'card'  }
];

const ICONS = {
  chat:  `<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z"/>`,
  trend: `<path d="m6 15 6-6 6 6"/>`,
  alert: `<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>`,
  card:  `<rect x="2" y="5" width="20" height="14" rx="3"/><path d="M2 10h20"/>`
};

export class NebulaNotificationPanel extends LitElement {
  static properties = {
    notifications: { type: Array },
    _open:         { state: true }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.notifications = DEFAULT_NOTIFICATIONS;
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
  _onGlobalClose = (e) => { if (e.detail?.except !== 'notifications') this._open = false; };

  _toggle(e) {
    e.stopPropagation();
    this._open = !this._open;
    if (this._open) {
      window.dispatchEvent(new CustomEvent('nebula:close-dropdowns', {
        detail: { except: 'notifications' }
      }));
    }
  }

  close() { this._open = false; }

  _unreadCount() { return this.notifications.filter(n => n.unread).length; }

  _svg(key) {
    const t = document.createElement('template');
    t.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg">${ICONS[key] || ''}</svg>`;
    const svg = t.content.querySelector('svg');
    return svg ? Array.from(svg.children).map(n => {
      const w = document.createElement('template');
      w.innerHTML = n.outerHTML;
      return w.content;
    }) : '';
  }

  render() {
    const unread = this._unreadCount();
    return html`
      <div class="dropdown-wrap ${this._open ? 'active' : ''}">
        <button class="icon-btn" type="button" aria-label="Notifications"
                aria-haspopup="true" aria-expanded="${this._open}"
                @click=${this._toggle}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 8.5a6 6 0 1 0-12 0c0 6-2.5 7.5-2.5 7.5h17S18 14.5 18 8.5z"/>
            <path d="M10.3 20a2 2 0 0 0 3.4 0"/>
          </svg>
          ${unread > 0 ? html`<span class="dot"></span>` : ''}
        </button>

        <div class="dropdown notif ${this._open ? 'open' : ''}" role="menu">
          <div class="dropdown-head">
            <h3>Notifications</h3>
            <span class="pill">${unread} new</span>
            <button type="button">Mark all read</button>
          </div>

          <div class="notif-list">
            ${this.notifications.map(n => html`
              <a class="notif-item ${n.unread ? 'unread' : ''}" href="#">
                <span class="notif-ico ${n.iconClass}">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                       stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    ${this._svg(n.icon)}
                  </svg>
                </span>
                <span class="notif-body">
                  <p><b>${n.title}</b> ${n.text}</p>
                  <span class="notif-time">${n.time}</span>
                </span>
              </a>
            `)}
          </div>

          <div class="dropdown-foot">
            <a href="#">View all notifications</a>
          </div>
        </div>
      </div>
    `;
  }
}

customElements.define('nebula-notification-panel', NebulaNotificationPanel);