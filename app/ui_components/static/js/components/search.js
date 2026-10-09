import { defineComponent, emit, escapeHtml } from '../_base.js';

/* ==========================================================================
   Icon paths
   ========================================================================== */
const ICONS = {
  clock: `<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>`,
  trend: `<path d="m6 15 6-6 6 6"/>`,
  coin:  `<path d="M12 2v20"/><path d="M17 6.5c0-1.9-2.2-3-5-3s-5 1.1-5 3 2.2 2.7 5 3 5 1.1 5 3-2.2 3-5 3-5-1.1-5-3"/>`,
  chart: `<path d="M3 3v18h18"/><path d="m7 15 4-5 3 3 5-7"/>`,
  chat:  `<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z"/>`,
  bag:   `<rect x="3" y="7" width="18" height="13" rx="3"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>`
};

const svgWrap = (path) => `
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    ${path}
  </svg>`;

/* ==========================================================================
   Default items — replaceable via setItems()
   ========================================================================== */
const DEFAULT_ITEMS = [
  { group: 'Recent',      label: 'BTC Prediction — Q4',    icon: 'clock', iconClass: 'icon-soft--indigo' },
  { group: 'Recent',      label: 'ETH Volatility Alert',   icon: 'trend', iconClass: 'icon-soft--green'  },
  { group: 'Recent',      label: 'SOL Momentum Model',     icon: 'coin',  iconClass: 'icon-soft--amber'  },
  { group: 'Suggestions', label: 'Market Overview',        icon: 'chart', iconClass: 'icon-soft--violet', sub: 'Live top-50 performance' },
  { group: 'Suggestions', label: 'Open Alerts',            icon: 'chat',  iconClass: 'icon-soft--rose',   sub: '32 unresolved signals' },
  { group: 'Suggestions', label: 'Portfolio Performance',  icon: 'bag',   iconClass: 'icon-soft--sky',    sub: 'Weekly analytics' }
];

const QUICK_CHIPS = ['All', 'Coins', 'Signals', 'Alerts', 'Models'];

/* ==========================================================================
   <ramz-search>
   ========================================================================== */
class RamzSearch extends HTMLElement {
  #desktopOpen = false;
  #mobileOpen  = false;
  #query       = '';
  #activeIndex = -1;
  #items       = DEFAULT_ITEMS.slice();
  #refs        = {};

  /* --------------------------------------------------------------
     Lifecycle
     -------------------------------------------------------------- */
  connectedCallback() {
    this._renderShell();
    this._cacheRefs();
    this._attachListeners();
    this._renderBodies();
  }

  disconnectedCallback() {
    this._detachListeners();
  }

  /* --------------------------------------------------------------
     Public API
     -------------------------------------------------------------- */
  openMobile() {
    if (this.#mobileOpen) return;
    this.#mobileOpen = true;
    this._sync();
    emit(this, 'ramz:close-dropdowns', { except: 'search' });

    // Focus after the open transition finishes
    setTimeout(() => this.#refs.mobileInput?.focus(), 180);
  }

  closeMobile() {
    if (!this.#mobileOpen) return;
    this.#mobileOpen = false;
    this._sync();
    this._resetQuery();
  }

  focusDesktop() {
    if (window.innerWidth <= 860) return;
    this.#desktopOpen = true;
    this._sync();
    this.#refs.desktopInput?.focus();
  }

  close() {
    let changed = false;
    if (this.#desktopOpen) { this.#desktopOpen = false; changed = true; }
    if (this.#mobileOpen)  { this.#mobileOpen  = false; changed = true; }
    if (changed) this._sync();
  }

  setItems(list) {
    if (!Array.isArray(list)) return;
    this.#items = list.slice();
    this._renderBodies();
  }

  /* --------------------------------------------------------------
     Shell (built once)
     -------------------------------------------------------------- */
  _renderShell() {
    this.innerHTML = `
      <!-- Desktop: inline input + attached dropdown -->
      <div class="search">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="11" cy="11" r="7"/>
          <path d="m20 20-3.2-3.2"/>
        </svg>

        <input type="text" class="search-input"
               placeholder="Search markets, coins, alerts..."
               autocomplete="off"
               spellcheck="false"
               aria-haspopup="listbox"
               aria-expanded="false" />

        <kbd>⌘K</kbd>

        <div class="search-dropdown" role="listbox">
          <div class="search-panel-body" data-body="desktop"></div>
        </div>
      </div>

      <!-- Mobile: trigger button -->
      <button class="search-btn" type="button" aria-label="Open search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round">
          <circle cx="11" cy="11" r="7"/>
          <path d="m20 20-3.2-3.2"/>
        </svg>
      </button>

      <!-- Mobile: full-screen modal -->
      <div class="search-modal" role="dialog" aria-modal="true" aria-label="Search">
        <div class="search-modal-backdrop" data-action="close-mobile"></div>
        <div class="search-panel">
          <div class="search-panel-input">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round">
              <circle cx="11" cy="11" r="7"/>
              <path d="m20 20-3.2-3.2"/>
            </svg>
            <input type="text" class="search-input-mobile"
                   placeholder="Search coins, alerts, models..."
                   autocomplete="off"
                   spellcheck="false" />
            <span class="esc" data-action="close-mobile">ESC</span>
          </div>
          <div class="search-panel-body" data-body="mobile"></div>
        </div>
      </div>
    `;
  }

  _cacheRefs() {
    this.#refs = {
      searchWrap:     this.querySelector('.search'),
      desktopInput:   this.querySelector('.search-input'),
      desktopDropdown: this.querySelector('.search-dropdown'),
      desktopBody:    this.querySelector('[data-body="desktop"]'),
      mobileBtn:      this.querySelector('.search-btn'),
      modal:          this.querySelector('.search-modal'),
      mobileInput:    this.querySelector('.search-input-mobile'),
      mobileBody:     this.querySelector('[data-body="mobile"]')
    };
  }

  /* --------------------------------------------------------------
     Body rendering (dynamic)
     -------------------------------------------------------------- */
  _renderBodies() {
    const grouped = this._groupedItems();
    const html = Object.keys(grouped).length > 0
      ? this._renderGroupsHtml(grouped) + this._renderChipsHtml()
      : this._renderEmptyHtml();

    if (this.#refs.desktopBody) this.#refs.desktopBody.innerHTML = html;
    if (this.#refs.mobileBody)  this.#refs.mobileBody.innerHTML  = html;

    this._applyActive();
  }

  _groupedItems() {
    const q = this.#query.trim().toLowerCase();
    const filtered = q
      ? this.#items.filter(i => i.label.toLowerCase().includes(q))
      : this.#items;

    const groups = {};
    for (const item of filtered) {
      (groups[item.group] ||= []).push(item);
    }
    return groups;
  }

  _renderGroupsHtml(groups) {
    return Object.entries(groups).map(([groupName, items]) => `
      <div class="search-group">
        <div class="search-group-title">${escapeHtml(groupName)}</div>
        ${items.map(item => this._renderRowHtml(item)).join('')}
      </div>
    `).join('');
  }

  _renderRowHtml(item) {
    const sub  = item.sub  ? `<div class="row-sub">${escapeHtml(item.sub)}</div>` : '';
    const icon = ICONS[item.icon] || ICONS.clock;

    return `
      <div class="search-row" data-searchable="${escapeHtml(item.label)}" tabindex="-1">
        <span class="ico ${escapeHtml(item.iconClass || '')}">${svgWrap(icon)}</span>
        <div class="row-main">
          ${escapeHtml(item.label)}
          ${sub}
        </div>
        <span class="row-arrow">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round"
               stroke-linejoin="round">
            <path d="M5 12h14M13 6l6 6-6 6"/>
          </svg>
        </span>
      </div>
    `;
  }

  _renderChipsHtml() {
    return `
      <div class="search-group">
        <div class="search-group-title">Quick Filters</div>
        <div class="search-chips">
          ${QUICK_CHIPS.map(label => `
            <span class="search-chip" data-chip="${escapeHtml(label)}">${escapeHtml(label)}</span>
          `).join('')}
        </div>
      </div>
    `;
  }

  _renderEmptyHtml() {
    return `
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

  /* --------------------------------------------------------------
     Keyboard navigation
     -------------------------------------------------------------- */
  _getVisibleRows() {
    return Array.from(
      this.#refs.desktopBody?.querySelectorAll('.search-row') || []
    );
  }

  _setActiveIndex(idx) {
    const rows = this._getVisibleRows();
    if (rows.length === 0) { this.#activeIndex = -1; return; }

    if (idx < 0)              idx = rows.length - 1;
    if (idx >= rows.length)   idx = 0;

    this.#activeIndex = idx;
    this._applyActive();
    rows[idx].scrollIntoView({ block: 'nearest' });
  }

  _applyActive() {
    const rows = this._getVisibleRows();
    rows.forEach((r, i) => r.classList.toggle('active', i === this.#activeIndex));
  }

  /* --------------------------------------------------------------
     State helpers
     -------------------------------------------------------------- */
  _setQuery(q) {
    this.#query = q;
    if (this.#refs.desktopInput && this.#refs.desktopInput.value !== q) {
      this.#refs.desktopInput.value = q;
    }
    if (this.#refs.mobileInput && this.#refs.mobileInput.value !== q) {
      this.#refs.mobileInput.value = q;
    }
    this.#activeIndex = -1;
    this._renderBodies();
  }

  _resetQuery() {
    this.#query = '';
    this.#activeIndex = -1;
    if (this.#refs.desktopInput) this.#refs.desktopInput.value = '';
    if (this.#refs.mobileInput)  this.#refs.mobileInput.value  = '';
    this._renderBodies();
  }

  _sync() {
    const { searchWrap, desktopDropdown, desktopInput, modal } = this.#refs;

    searchWrap?.classList.toggle('open', this.#desktopOpen);
    desktopDropdown?.classList.toggle('open', this.#desktopOpen);
    desktopInput?.setAttribute('aria-expanded', String(this.#desktopOpen));

    modal?.classList.toggle('open', this.#mobileOpen);
    document.body.classList.toggle('no-scroll', this.#mobileOpen);
  }

  /* --------------------------------------------------------------
     Listeners
     -------------------------------------------------------------- */
  _attachListeners() {
    // Delegated click handling on the component subtree
    this.addEventListener('click', this._onClick);

    // Document click closes the desktop dropdown
    document.addEventListener('click', this._onDocumentClick);

    // Early pointer handling — used for the mobile modal's backdrop
    this.addEventListener('pointerdown', this._onPointerDown);

    // Global coordination
    window.addEventListener('ramz:close-dropdowns', this._onGlobalClose);

    

    // Desktop input
    const di = this.#refs.desktopInput;
    if (di) {
      di.addEventListener('input',   this._onDesktopInput);
      di.addEventListener('focus',   this._onDesktopFocus);
      di.addEventListener('click',   this._onDesktopFocus);
      di.addEventListener('keydown', this._onDesktopKeydown);
    }

    // Mobile input
    const mi = this.#refs.mobileInput;
    if (mi) {
      mi.addEventListener('input',   this._onMobileInput);
      mi.addEventListener('keydown', this._onMobileKeydown);
    }
  }

  _detachListeners() {
    this.removeEventListener('click', this._onClick);
    this.removeEventListener('pointerdown', this._onPointerDown);
    document.removeEventListener('click', this._onDocumentClick);
    window.removeEventListener('ramz:close-dropdowns', this._onGlobalClose);

    const di = this.#refs.desktopInput;
    if (di) {
      di.removeEventListener('input',   this._onDesktopInput);
      di.removeEventListener('focus',   this._onDesktopFocus);
      di.removeEventListener('click',   this._onDesktopFocus);
      di.removeEventListener('keydown', this._onDesktopKeydown);
    }

    const mi = this.#refs.mobileInput;
    if (mi) {
      mi.removeEventListener('input',   this._onMobileInput);
      mi.removeEventListener('keydown', this._onMobileKeydown);
    }

    // Safety net: make sure the body scroll is restored if the component
    // is removed while the mobile modal is open.
    document.body.classList.remove('no-scroll');
  }

  /* --------------------------------------------------------------
     Event handlers
     -------------------------------------------------------------- */
  _onClick = (e) => {
    // Mobile trigger button
    const trigger = e.target.closest('.search-btn');
    if (trigger && this.contains(trigger)) {
      e.stopPropagation();
      this.openMobile();
      return;
    }

    // Backdrop or ESC span
    const closeMobileBtn = e.target.closest('[data-action="close-mobile"]');
    if (closeMobileBtn && this.contains(closeMobileBtn)) {
      this.closeMobile();
      return;
    }

    // Result row
    const row = e.target.closest('.search-row');
    if (row && this.contains(row)) {
      this._onRowClick(row);
      return;
    }

    // Quick-filter chip
    const chip = e.target.closest('.search-chip');
    if (chip && this.contains(chip)) {
      const value = chip.dataset.chip || chip.textContent.trim();
      this._setQuery(value === 'All' ? '' : value);
      this.#refs.desktopInput?.focus();
    }
  };

  _onDocumentClick = (e) => {
    if (!this.contains(e.target)) {
      if (this.#desktopOpen) {
        this.#desktopOpen = false;
        this._sync();
      }
    }
  };

  _onGlobalClose = (e) => {
    if (e.detail?.except !== 'search') {
      this.close();
    }
  };

  _onDesktopFocus = () => {
    if (this.#desktopOpen) return;
    this.#desktopOpen = true;
    this._sync();
    emit(this, 'ramz:close-dropdowns', { except: 'search' });
  };

  _onDesktopInput = (e) => {
    this.#query = e.target.value;
    this.#activeIndex = -1;
    this._renderBodies();
    if (!this.#desktopOpen) {
      this.#desktopOpen = true;
      this._sync();
    }
  };

  _onDesktopKeydown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this._setActiveIndex(this.#activeIndex + 1);
      return;
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      this._setActiveIndex(this.#activeIndex - 1);
      return;
    }

    if (e.key === 'Enter') {
      const rows = this._getVisibleRows();
      if (this.#activeIndex >= 0 && this.#activeIndex < rows.length) {
        e.preventDefault();
        this._onRowClick(rows[this.#activeIndex]);
      }
      return;
    }

    if (e.key === 'Escape') {
      e.preventDefault();
      this.#desktopOpen = false;
      this._sync();
      e.target.blur();
    }
  };

  _onMobileInput = (e) => {
    this.#query = e.target.value;
    this.#activeIndex = -1;
    this._renderBodies();
  };

  _onMobileKeydown = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      this.closeMobile();
    }
  };

  /* --------------------------------------------------------------
   Mobile backdrop close (fires before the keyboard is dismissed)
   -------------------------------------------------------------- */
_onPointerDown = (e) => {
  if (!this.#mobileOpen) return;

  const target = e.target.closest('[data-action="close-mobile"]');
  if (target && this.contains(target)) {
    this.closeMobile();
  }
};

  _onRowClick(row) {
    const label = row.dataset.searchable || row.textContent.trim();
    this._setQuery(label);
    this.close();
    this.#refs.desktopInput?.blur();
    emit(this, 'ramz:search-select', { label });
  }
}

defineComponent('ramz-search', RamzSearch);