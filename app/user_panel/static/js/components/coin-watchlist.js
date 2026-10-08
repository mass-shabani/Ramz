import { defineComponent, attr, emit, escapeHtml } from '../_base.js';

/* ==========================================================================
   Default demo data — replace via setItems() or the `endpoint` attribute
   ========================================================================== */
const DEFAULT_ITEMS = [
  { symbol: '₿', avatarClass: 'avatar--amber',  name: 'Bitcoin',  pair: 'BTC / USDT', signal: 'Bullish', confidence: 72, confidenceClass: 'active',  price: 63480,   change:  2.4 },
  { symbol: 'Ξ', avatarClass: 'avatar--violet', name: 'Ethereum', pair: 'ETH / USDT', signal: 'Neutral', confidence: 48, confidenceClass: 'pending', price: 3180,    change:  0.9 },
  { symbol: '◎', avatarClass: 'avatar--indigo', name: 'Solana',   pair: 'SOL / USDT', signal: 'Bullish', confidence: 81, confidenceClass: 'active',  price: 152.4,   change:  5.1 },
  { symbol: '₮', avatarClass: 'avatar--green',  name: 'Cardano',  pair: 'ADA / USDT', signal: 'Bearish', confidence: 28, confidenceClass: 'idle',    price: 0.482,   change: -1.2 },
  { symbol: '✕', avatarClass: 'avatar--sky',    name: 'Ripple',   pair: 'XRP / USDT', signal: 'Bullish', confidence: 68, confidenceClass: 'active',  price: 0.612,   change:  3.6 }
];

/* ==========================================================================
   Helpers
   ========================================================================== */
function formatPrice(value) {
  if (!Number.isFinite(value)) return '—';
  if (value >= 1000)  return '$' + value.toLocaleString('en-US', { maximumFractionDigits: 0 });
  if (value >= 1)     return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return '$' + value.toFixed(3);
}

function formatChange(value) {
  if (!Number.isFinite(value)) return { text: '—', direction: '' };
  const sign = value > 0 ? '+' : '';
  return {
    text: `${sign}${value.toFixed(1)}%`,
    direction: value > 0 ? 'up' : value < 0 ? 'down' : ''
  };
}

/**
 * <ramz-coin-watchlist>
 *
 * A card containing a table of coins with signal, confidence, price
 * and 24h change columns.
 *
 * Attributes:
 *   • title        — card title
 *   • subtitle     — card subtitle
 *   • endpoint     — optional URL to POST for live data (returns JSON array)
 *   • add-label    — label for the CTA button (default: "Add Coin")
 *   • hide-add     — if present, the CTA button is not rendered
 *
 * Public API:
 *   • setItems(list)  — replace the coin list
 *   • reload()        — if `endpoint` is set, re-fetch the data
 *
 * Emits:
 *   • ramz:watchlist-add — when the CTA button is clicked
 */
class CoinWatchlist extends HTMLElement {
  static get observedAttributes() {
    return ['title', 'subtitle', 'add-label', 'hide-add'];
  }

  #items    = [];
  #refs     = {};
  #loaded   = false;
  #fetching = false;

  connectedCallback() {
    if (!this.#loaded) {
      this.#items = DEFAULT_ITEMS.slice();
      this.#loaded = true;
    }

    this._render();
    this._cacheRefs();
    this._attachListeners();
    this._renderRows();

    const endpoint = attr(this, 'endpoint', '');
    if (endpoint) this.reload();
  }

  disconnectedCallback() {
    this._detachListeners();
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal) return;
    if (!this.isConnected) return;

    // Structural attributes need a rebuild
    this._render();
    this._cacheRefs();
    this._attachListeners();
    this._renderRows();
  }

  /* --------------------------------------------------------------
     Public API
     -------------------------------------------------------------- */
  setItems(list) {
    if (!Array.isArray(list)) return;
    this.#items = list.slice();
    if (this.isConnected) this._renderRows();
  }

  async reload() {
    const endpoint = attr(this, 'endpoint', '');
    if (!endpoint || this.#fetching) return;

    this.#fetching = true;
    this._setLoading(true);

    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json'
        },
        credentials: 'same-origin'
      });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);

      const data = await resp.json();
      if (Array.isArray(data)) this.setItems(data);

    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[coin-watchlist] fetch failed:', err);
      this._setLoading(false, true);

    } finally {
      this.#fetching = false;
      this._setLoading(false);
    }
  }

  /* --------------------------------------------------------------
     Shell
     -------------------------------------------------------------- */
  _render() {
    const title     = attr(this, 'title',    'Watchlist');
    const subtitle  = attr(this, 'subtitle', "Coins you're tracking in real time");
    const addLabel  = attr(this, 'add-label', 'Add Coin');
    const hideAdd   = this.hasAttribute('hide-add');

    this.innerHTML = `
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-head-text">
              <div class="card-title">${escapeHtml(title)}</div>
              <div class="card-sub">${escapeHtml(subtitle)}</div>
            </div>
          </div>
          ${hideAdd ? '' : `
            <div class="card-head-actions">
              <button class="btn-primary" type="button" data-action="add">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="2.2" stroke-linecap="round">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
                ${escapeHtml(addLabel)}
              </button>
            </div>
          `}
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Coin</th>
                <th>Signal</th>
                <th>Confidence</th>
                <th>Price</th>
                <th>24h</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    `;
  }

  _cacheRefs() {
    this.#refs = {
      tbody:   this.querySelector('tbody'),
      addBtn:  this.querySelector('[data-action="add"]')
    };
  }

  /* --------------------------------------------------------------
     Rendering
     -------------------------------------------------------------- */
  _renderRows() {
    const tbody = this.#refs.tbody;
    if (!tbody) return;

    if (this.#items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align:center;padding:32px;color:var(--muted);">
            No coins in your watchlist yet.
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = this.#items.map(item => this._renderRow(item)).join('');
  }

  _renderRow(item) {
    const change  = formatChange(item.change);
    const changeColor = change.direction === 'up'   ? 'color:#34d399'
                       : change.direction === 'down' ? 'color:#fb7185'
                       : '';

    const conf = Number.isFinite(item.confidence) ? `${item.confidence}%` : '—';
    const confClass = item.confidenceClass || 'idle';

    return `
      <tr>
        <td>
          <div class="cell-user">
            <span class="avatar ${escapeHtml(item.avatarClass || '')}">${escapeHtml(item.symbol || '')}</span>
            <div>
              <div class="cu-name">${escapeHtml(item.name || '')}</div>
              <div class="cu-mail">${escapeHtml(item.pair || '')}</div>
            </div>
          </div>
        </td>
        <td>${escapeHtml(item.signal || '—')}</td>
        <td><span class="status ${escapeHtml(confClass)}">${escapeHtml(conf)} up</span></td>
        <td class="amount">${formatPrice(item.price)}</td>
        <td class="amount" style="${changeColor}">${change.text}</td>
      </tr>
    `;
  }

  _setLoading(isLoading, isError = false) {
    const card = this.querySelector('.card');
    if (!card) return;
    card.classList.toggle('is-loading', isLoading);
    card.classList.toggle('is-error',   isError);
  }

  /* --------------------------------------------------------------
     Listeners
     -------------------------------------------------------------- */
  _attachListeners() {
    this.addEventListener('click', this._onClick);
  }

  _detachListeners() {
    this.removeEventListener('click', this._onClick);
  }

  _onClick = (e) => {
    const addBtn = e.target.closest('[data-action="add"]');
    if (addBtn && this.contains(addBtn)) {
      emit(this, 'ramz:watchlist-add');
    }
  };
}

defineComponent('ramz-coin-watchlist', CoinWatchlist);