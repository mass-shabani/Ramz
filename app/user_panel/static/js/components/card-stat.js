import { LitElement, html } from '../lit-import.js';

export class NebulaCardStat extends LitElement {
  static properties = {
    label:       { type: String },
    value:       { type: String },
    iconClass:   { type: String },
    trend:       { type: String },   // 'up' | 'down' | ''
    trendValue:  { type: String },
    trendLabel:  { type: String }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.trend = '';
  }

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