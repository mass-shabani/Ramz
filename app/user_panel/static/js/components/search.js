import { LitElement, html } from '../lit-import.js';

const DEFAULT_ITEMS = [
  { group: 'Recent',      label: 'BTC Prediction — Q4',    iconClass: 'icon-soft--indigo', icon: 'clock' },
  { group: 'Recent',      label: 'ETH Volatility Alert',   iconClass: 'icon-soft--green',  icon: 'trend' },
  { group: 'Recent',      label: 'SOL Momentum Model',     iconClass: 'icon-soft--amber',  icon: 'coin'  },
  { group: 'Suggestions', label: 'Market Overview',        iconClass: 'icon-soft--violet', icon: 'chart', sub: 'Live top-50 performance' },
  { group: 'Suggestions', label: 'Open Alerts',            iconClass: 'icon-soft--rose',   icon: 'chat',  sub: '32 unresolved signals' },
  { group: 'Suggestions', label: 'Portfolio Performance',  iconClass: 'icon-soft--sky',    icon: 'bag',   sub: 'Weekly analytics' }
];

const ICONS = {
  clock: `<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>`,
  trend: `<path d="m6 15 6-6 6 6"/>`,
  coin:  `<path d="M12 2v20"/><path d="M17 6.5c0-1.9-2.2-3-5-3s-5 1.1-5 3 2.2 2.7 5 3 5 1.1 5 3-2.2 3-5 3-5-1.1-5-3"/>`,
  chart: `<path d="M3 3v18h18"/><path d="m7 15 4-5 3 3 5-7"/>`,
  chat:  `<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z"/>`,
  bag:   `<rect x="3" y="7" width="18" height="13" rx="3"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>`
};

export class NebulaSearch extends LitElement {
  static properties = {
    placeholder:  { type: String },
    _desktopOpen: { state: true },
    _mobileOpen:  { state: true },
    _query:       { state: true }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.placeholder = 'Search markets, coins, alerts...';
    this._desktopOpen = false;
    this._mobileOpen = false;
    this._query = '';
    this._items = DEFAULT_ITEMS;
  }

  connectedCallback() {
    super.connectedCallback();
    document.addEventListener('click', this._onDocClick);
  }

  disconnectedCallback() {
    document.removeEventListener('click', this._onDocClick);
    super.disconnectedCallback();
  }

  _onDocClick = (e) => {
    if (!this.contains(e.target)) this._desktopOpen = false;
  };

  _openDesktop() {
    if (window.innerWidth <= 860) return;
    this._desktopOpen = true;
  }

  focusDesktop() {
    this._openDesktop();
    this.querySelector('#searchInputDesktop')?.focus();
  }

  openMobile() { this._mobileOpen = true; }
  closeMobile() { this._mobileOpen = false; }
  close() { this._desktopOpen = false; this._mobileOpen = false; }

  _onDesktopInput(e) { this._query = e.target.value; }

  _onRowClick(label) {
    this._query = label;
    this._desktopOpen = false;
    const input = this.querySelector('#searchInputDesktop');
    if (input) input.value = label;
  }

  _onChipClick(value) {
    this._query = value === 'All' ? '' : value;
    const input = this.querySelector('#searchInputDesktop');
    if (input) { input.value = this._query; input.focus(); }
  }

  _filtered() {
    const q = (this._query || '').trim().toLowerCase();
    if (!q) return this._items;
    return this._items.filter(i => i.label.toLowerCase().includes(q));
  }

  _grouped() {
    const items = this._filtered();
    const groups = {};
    for (const it of items) {
      (groups[it.group] ||= []).push(it);
    }
    return groups;
  }

  _renderIcon(iconKey, iconClass) {
    return html`
      <span class="ico ${iconClass}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          ${this._svgContent(iconKey)}
        </svg>
      </span>
    `;
  }

  _svgContent(key) {
    const path = ICONS[key] || '';
    // Use a <template> to safely inject the path markup
    const tpl = document.createElement('template');
    tpl.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg">${path}</svg>`;
    const svg = tpl.content.querySelector('svg');
    return svg ? Array.from(svg.children).map(n => {
      const t = document.createElement('template');
      t.innerHTML = n.outerHTML;
      return t.content;
    }) : '';
  }

  _renderDropdownBody() {
    const groups = this._grouped();
    const hasResults = Object.keys(groups).length > 0;

    if (!hasResults) {
      return html`
        <div class="search-empty show">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7"/>
            <path d="m20 20-3.2-3.2"/>
            <path d="M9 9h4"/>
          </svg>
          No results found. Try a different search term.
        </div>
      `;
    }

    return html`
      ${Object.entries(groups).map(([groupName, items]) => html`
        <div class="search-group">
          <div class="search-group-title">${groupName}</div>
          ${items.map(item => html`
            <div class="search-row" @click=${() => this._onRowClick(item.label)}>
              ${this._renderIcon(item.icon, item.iconClass)}
              <div class="row-main">
                ${item.label}
                ${item.sub ? html`<div class="row-sub">${item.sub}</div>` : ''}
              </div>
              <span class="row-arrow">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none"
                     stroke="currentColor" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12h14M13 6l6 6-6 6"/>
                </svg>
              </span>
            </div>
          `)}
        </div>
      `)}

      <div class="search-group">
        <div class="search-group-title">Quick Filters</div>
        <div class="search-chips">
          ${['All', 'Coins', 'Signals', 'Alerts', 'Models'].map(label => html`
            <span class="search-chip" @click=${() => this._onChipClick(label)}>${label}</span>
          `)}
        </div>
      </div>
    `;
  }

  render() {
    return html`
      <!-- Desktop: inline input + attached dropdown -->
      <div class="search ${this._desktopOpen ? 'open' : ''}" id="searchWrap">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round">
          <circle cx="11" cy="11" r="7"/>
          <path d="m20 20-3.2-3.2"/>
        </svg>
        <input type="text" id="searchInputDesktop"
               placeholder="${this.placeholder}"
               autocomplete="off"
               @focus=${this._openDesktop}
               @click=${this._openDesktop}
               @input=${this._onDesktopInput} />
        <kbd>⌘K</kbd>

        <div class="search-dropdown ${this._desktopOpen ? 'open' : ''}">
          <div class="search-panel-body">${this._renderDropdownBody()}</div>
        </div>
      </div>

      <!-- Mobile: trigger button -->
      <button class="search-btn" type="button" aria-label="Open search"
              @click=${this.openMobile}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round">
          <circle cx="11" cy="11" r="7"/>
          <path d="m20 20-3.2-3.2"/>
        </svg>
      </button>

      <!-- Mobile: full-screen modal -->
      <div class="search-modal ${this._mobileOpen ? 'open' : ''}" role="dialog" aria-modal="true">
        <div class="search-modal-backdrop" @click=${this.closeMobile}></div>
        <div class="search-panel">
          <div class="search-panel-input">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round">
              <circle cx="11" cy="11" r="7"/>
              <path d="m20 20-3.2-3.2"/>
            </svg>
            <input type="text" placeholder="Search coins, alerts, models..."
                   autocomplete="off" @input=${this._onDesktopInput} />
            <span class="esc" @click=${this.closeMobile}>ESC</span>
          </div>
          <div class="search-panel-body">${this._renderDropdownBody()}</div>
        </div>
      </div>
    `;
  }
}

customElements.define('nebula-search', NebulaSearch);