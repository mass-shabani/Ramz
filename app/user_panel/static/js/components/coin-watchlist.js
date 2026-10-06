import { LitElement, html } from '../lit-import.js';

const DEFAULT_COINS = [
  { symbol: '₿', avatarClass: 'avatar--amber',  name: 'Bitcoin',  pair: 'BTC / USDT', signal: 'Bullish', conf: '72% up', confClass: 'active',  price: '$63,480', change:  2.4 },
  { symbol: 'Ξ', avatarClass: 'avatar--violet', name: 'Ethereum', pair: 'ETH / USDT', signal: 'Neutral', conf: '48% up', confClass: 'pending', price: '$3,180',  change:  0.9 },
  { symbol: '◎', avatarClass: 'avatar--indigo', name: 'Solana',   pair: 'SOL / USDT', signal: 'Bullish', conf: '81% up', confClass: 'active',  price: '$152.40', change:  5.1 },
  { symbol: '₮', avatarClass: 'avatar--green',  name: 'Cardano',  pair: 'ADA / USDT', signal: 'Bearish', conf: '28% up', confClass: 'idle',    price: '$0.482',  change: -1.2 },
  { symbol: '✕', avatarClass: 'avatar--sky',    name: 'Ripple',   pair: 'XRP / USDT', signal: 'Bullish', conf: '68% up', confClass: 'active',  price: '$0.612',  change:  3.6 }
];

export class CoinWatchlist extends LitElement {
  static properties = {
    title:    { type: String },
    subtitle: { type: String },
    coins:    { type: Array }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.title = 'Watchlist';
    this.subtitle = "Coins you're tracking in real time";
    this.coins = DEFAULT_COINS;
  }

  _addCoin() {
    this.dispatchEvent(new CustomEvent('add-coin', { bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div class="card">
        <div class="card-head">
          <div>
            <div class="card-title">${this.title}</div>
            <div class="card-sub">${this.subtitle}</div>
          </div>
          <button class="btn-primary" type="button" @click=${this._addCoin}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2.2" stroke-linecap="round">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            Add Coin
          </button>
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
            <tbody>
              ${this.coins.map(c => html`
                <tr>
                  <td>
                    <div class="cell-user">
                      <span class="avatar ${c.avatarClass}">${c.symbol}</span>
                      <div>
                        <div class="cu-name">${c.name}</div>
                        <div class="cu-mail">${c.pair}</div>
                      </div>
                    </div>
                  </td>
                  <td>${c.signal}</td>
                  <td><span class="status ${c.confClass}">${c.conf}</span></td>
                  <td class="amount">${c.price}</td>
                  <td class="amount" style="color:${c.change > 0 ? '#34d399' : '#fb7185'}">
                    ${c.change > 0 ? '+' : ''}${c.change}%
                  </td>
                </tr>
              `)}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }
}

customElements.define('nebula-coin-watchlist', CoinWatchlist);