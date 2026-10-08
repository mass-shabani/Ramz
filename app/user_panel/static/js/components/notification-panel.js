import { defineComponent, emit } from '../_base.js';

/* --------------------------------------------------------------
   Inline SVG icons (kept as constants to avoid repetition)
   -------------------------------------------------------------- */
const ICONS = {
  chat:  `<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z"/>`,
  trend: `<path d="m6 15 6-6 6 6"/>`,
  alert: `<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>`,
  card:  `<rect x="2" y="5" width="20" height="14" rx="3"/><path d="M2 10h20"/>`
};

const ICON_WRAPPER = (path) => `
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    ${path}
  </svg>`;

/* --------------------------------------------------------------
   Default demo data — replace with real data via setNotifications()
   -------------------------------------------------------------- */
const DEFAULT_NOTIFICATIONS = [
  {
    unread: true,
    icon: 'chat',
    iconClass: 'icon-soft--indigo',
    title: 'BTC prediction updated',
    text: '— 72% bullish confidence.',
    time: '2 minutes ago'
  },
  {
    unread: true,
    icon: 'trend',
    iconClass: 'icon-soft--green',
    title: 'ETH crossed target',
    text: '— crossed your target of $3,200.',
    time: '18 minutes ago'
  },
  {
    unread: true,
    icon: 'alert',
    iconClass: 'icon-soft--amber',
    title: 'Volatility detected',
    text: '— unusual volatility on SOL/USDT.',
    time: '1 hour ago'
  },
  {
    unread: true,
    icon: 'card',
    iconClass: 'icon-soft--rose',
    title: 'Weekly AI report ready',
    text: '— +18.4% signal accuracy.',
    time: '3 hours ago'
  }
];

/**
 * <ramz-notifications>
 *
 * Bell button + notification dropdown.
 *
 * Public API:
 *   • open()               — open the dropdown
 *   • close()              — close the dropdown
 *   • toggle()             — toggle the dropdown
 *   • setNotifications(l)  — replace the list of notifications
 *
 * Emits:
 *   • ramz:notifications-read-all — when the "Mark all read" button is clicked
 */
class RamzNotifications extends HTMLElement {
  #open = false;
  #notifications = [];
  #refs = {};

  connectedCallback() {
    if (this.#notifications.length === 0) {
      this.#notifications = DEFAULT_NOTIFICATIONS.slice();
    }

    this._render();
    this._cacheRefs();
    this._attachListeners();
    this._renderContent();
  }

  disconnectedCallback() {
    this._detachListeners();
  }

  /* --------------------------------------------------------------
     Public API
     -------------------------------------------------------------- */
  open() {
    if (this.#open) return;
    this.#open = true;
    this._sync();

    // Tell other dropdowns to close
    emit(this, 'ramz:close-dropdowns', { except: 'notifications' });
  }

  close() {
    if (!this.#open) return;
    this.#open = false;
    this._sync();
  }

  toggle() {
    this.#open ? this.close() : this.open();
  }

  setNotifications(list) {
    if (!Array.isArray(list)) return;
    this.#notifications = list.slice();
    this._renderContent();
  }

  /* --------------------------------------------------------------
     Rendering
     -------------------------------------------------------------- */
  _render() {
    this.innerHTML = `
      <div class="dropdown-wrap">
        <button class="icon-btn" type="button"
                aria-label="Notifications"
                aria-haspopup="true"
                aria-expanded="false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 8.5a6 6 0 1 0-12 0c0 6-2.5 7.5-2.5 7.5h17S18 14.5 18 8.5z"/>
            <path d="M10.3 20a2 2 0 0 0 3.4 0"/>
          </svg>
          <span class="dot" hidden></span>
        </button>

        <div class="dropdown notif" role="menu">
          <div class="dropdown-head">
            <h3>Notifications</h3>
            <span class="pill">0 new</span>
            <button type="button" data-action="mark-all-read">Mark all read</button>
          </div>
          <div class="notif-list"></div>
          <div class="dropdown-foot">
            <a href="#">View all notifications</a>
          </div>
        </div>
      </div>
    `;
  }

  _cacheRefs() {
    const root = this.querySelector('.dropdown-wrap');
    this.#refs = {
      root,
      trigger: root.querySelector('.icon-btn'),
      dot:     root.querySelector('.dot'),
      panel:   root.querySelector('.dropdown'),
      pill:    root.querySelector('.pill'),
      list:    root.querySelector('.notif-list'),
      markAll: root.querySelector('[data-action="mark-all-read"]')
    };
  }

  _renderContent() {
    const { list, pill, dot } = this.#refs;
    if (!list) return;

    /* ---- list ---- */
    if (this.#notifications.length === 0) {
      list.innerHTML = `
        <div style="padding:32px 16px;text-align:center;color:var(--muted);font-size:13px;">
          You're all caught up.
        </div>`;
    } else {
      list.innerHTML = this.#notifications.map(n => `
        <a class="notif-item ${n.unread ? 'unread' : ''}" href="#">
          <span class="notif-ico ${n.iconClass || ''}">
            ${ICON_WRAPPER(ICONS[n.icon] || '')}
          </span>
          <span class="notif-body">
            <p><b>${n.title}</b> ${n.text || ''}</p>
            <span class="notif-time">${n.time || ''}</span>
          </span>
        </a>
      `).join('');
    }

    /* ---- pill + dot ---- */
    const unread = this.#notifications.filter(n => n.unread).length;
    pill.textContent = `${unread} new`;

    if (dot) dot.hidden = unread === 0;

    /* ---- disable mark-all when nothing unread ---- */
    if (this.#refs.markAll) {
      this.#refs.markAll.disabled = unread === 0;
      this.#refs.markAll.style.opacity = unread === 0 ? '.4' : '';
      this.#refs.markAll.style.pointerEvents = unread === 0 ? 'none' : '';
    }
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
    /* Toggle button */
    const trigger = e.target.closest('.icon-btn');
    if (trigger && this.contains(trigger)) {
      e.stopPropagation();
      this.toggle();
      return;
    }

    /* Mark-all-read */
    const markAll = e.target.closest('[data-action="mark-all-read"]');
    if (markAll && this.contains(markAll)) {
      this._markAllRead();
      return;
    }
  };

  _onDocumentClick = (e) => {
    if (!this.contains(e.target)) this.close();
  };

  _onGlobalClose = (e) => {
    if (e.detail?.except !== 'notifications') this.close();
  };

  _markAllRead() {
    this.#notifications = this.#notifications.map(n => ({ ...n, unread: false }));
    this._renderContent();
    emit(this, 'ramz:notifications-read-all');
  }
}

defineComponent('ramz-notifications', RamzNotifications);