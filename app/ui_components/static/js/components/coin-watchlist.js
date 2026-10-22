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

/* ==========================================================================
   Column and row builders (delegated to <ramz-table>)
   ========================================================================== */
function buildColumns() {
  return [
    { key: '_coin',       label: 'Coin',       type: 'avatar' },
    { key: 'signal',      label: 'Signal',     type: 'text' },
    { key: '_confidence', label: 'Confidence', type: 'badge' },
    { key: 'price',       label: 'Price',      type: 'text', className: 'amount' },
    { key: '_change',     label: '24h',        type: 'html', className: 'amount' },
  ];
}

function buildRow(item) {
  const confValue   = Number.isFinite(item.confidence) ? `${item.confidence}%` : '—';
  const confText    = `${confValue} up`;
  const confVariant = item.confidenceClass || 'idle';

  const change = formatChange(item.change);
  const changeColor = change.direction === 'up'   ? '#34d399'
                    : change.direction === 'down' ? '#fb7185'
                    : '';
  const changeHtml = changeColor
    ? `<span style="color:${changeColor}">${escapeHtml(change.text)}</span>`
    : escapeHtml(change.text);

  return {
    _coin: {
      initials:    item.symbol,
      name:        item.name  || '',
      email:       item.pair  || '',
      avatarClass: item.avatarClass || '',
    },
    signal: item.signal || '—',
    _confidence: { text: confText, variant: confVariant },
    price:   formatPrice(item.price),
    _change: changeHtml,
  };
}

/* ==========================================================================
   <ramz-coin-watchlist>
   ========================================================================== */
/**
 * <ramz-coin-watchlist>
 *
 * A thin wrapper around <ramz-table> that renders the crypto watchlist.
 *
 * Attributes:
 *   • title        — card title (passed through)
 *   • subtitle     — card subtitle (passed through)
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
 *
 * The actual table markup, styling, and column types are owned by
 * <ramz-table>. This component only maps the coin schema (symbol/name/
 * pair/signal/confidence/price/change) into ramz-table's row format
 * and translates the "Add" click back into a custom event.
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
    this._render();
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

    } finally {
      this.#fetching = false;
      this._setLoading(false);
    }
  }

  /* --------------------------------------------------------------
     Shell
     -------------------------------------------------------------- */
  _render() {
    const title    = attr(this, 'title',    'Watchlist');
    const subtitle = attr(this, 'subtitle', "Coins you're tracking in real time");
    const addLabel = attr(this, 'add-label', 'Add Coin');
    const hideAdd  = this.hasAttribute('hide-add');

    this.innerHTML = '';

    const table = document.createElement('ramz-table');
    table.setAttribute('title', title);
    table.setAttribute('subtitle', subtitle);
    table.setAttribute('empty-text', 'No coins in your watchlist yet.');

    if (!hideAdd) {
      const btn = document.createElement('button');
      btn.className = 'btn-primary';
      btn.type = 'button';
      btn.setAttribute('data-action', 'add');
      btn.setAttribute('slot', 'header-actions');
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.2" stroke-linecap="round">
          <path d="M12 5v14M5 12h14"/>
        </svg>
        ${escapeHtml(addLabel)}
      `;
      table.appendChild(btn);
    }

    this.appendChild(table);

    table.setColumns(buildColumns());

    this.#refs.table = table;
  }

  /* --------------------------------------------------------------
     Data
     -------------------------------------------------------------- */
  _renderRows() {
    const table = this.#refs.table;
    if (!table) return;

    const rows = this.#items.map(buildRow);
    table.setData(rows);
  }

  _setLoading(isLoading) {
    if (this.#refs.table && typeof this.#refs.table.setLoading === 'function') {
      this.#refs.table.setLoading(isLoading);
    }
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