import { LitElement, html, css } from '../lit-import.js';

export class NebulaCardStat extends LitElement {
  static properties = {
    label:       { type: String },
    value:       { type: String },
    iconClass:   { type: String },
    trend:       { type: String },
    trendValue:  { type: String },
    trendLabel:  { type: String }
  };

  constructor() {
    super();
    this.trend = '';
  }

  createRenderRoot() { return this; }

  /* static styles commented out — managed globally in style.css */
  /* static styles = css`
    :host {
      display: block;
    }

    .card {
      position: relative;
      background: var(--glass-bg);
      backdrop-filter: var(--glass-blur);
      -webkit-backdrop-filter: var(--glass-blur);
      border: var(--glass-border);
      border-radius: var(--radius);
      padding: 20px;
      box-shadow: var(--glass-shadow);
      transition: border-color .25s, box-shadow .25s;
    }

    .card:hover {
      border-color: rgba(255, 255, 255, 0.14);
      box-shadow:
        0 12px 40px rgba(0, 0, 0, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.1),
        inset 0 -1px 0 rgba(0, 0, 0, 0.15);
    }

    .stat {
      position: relative;
      overflow: hidden;
    }

    .stat::after {
      content: '';
      position: absolute;
      top: -70px;
      right: -50px;
      width: 170px;
      height: 170px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(99,102,241,.22), transparent 70%);
      pointer-events: none;
    }

    .stat-top {
      position: relative;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 16px;
    }

    .stat-icon {
      width: 44px;
      height: 44px;
      border-radius: 13px;
      display: grid;
      place-items: center;
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.06);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.08);
    }

    .stat-icon svg {
      width: 21px;
      height: 21px;
    }

    .stat-label {
      font-size: 12.5px;
      font-weight: 500;
      color: var(--muted);
      text-align: right;
    }

    .stat-value {
      position: relative;
      font-size: 28px;
      font-weight: 800;
      letter-spacing: -1.2px;
      margin-bottom: 9px;
    }

    .trend {
      position: relative;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 11.5px;
      font-weight: 600;
    }

    .trend svg {
      width: 13px;
      height: 13px;
    }

    .trend.up {
      color: var(--success);
    }

    .trend.down {
      color: var(--danger);
    }

    .trend span {
      color: var(--muted);
      font-weight: 500;
    }
  `; */

  render() {
    return html`
      <div class="card stat">
        <div class="stat-top">
          <span class="stat-icon ${this.iconClass}"><slot name="icon"></slot></span>
          <span class="stat-label">${this.label}</span>
        </div>
        <div class="stat-value">${this.value}</div>
        ${this.trend ? html`
          <div class="trend ${this.trend}">
            ${this.trend === 'up'
              ? html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                          stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                 <path d="m6 15 6-6 6 6"/>
               </svg>`
              : html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                          stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                 <path d="m6 9 6 6 6-6"/>
               </svg>`}
            ${this.trendValue} <span>${this.trendLabel}</span>
          </div>
        ` : ''}
      </div>
    `;
  }
}

customElements.define('nebula-card-stat', NebulaCardStat);
