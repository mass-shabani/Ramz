import { LitElement, html } from '../lit-import.js';

export class NebulaCardContent extends LitElement {
  static properties = {
    title:    { type: String },
    subtitle: { type: String }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.title = '';
    this.subtitle = '';
  }

  render() {
    const hasHeader = this.title || this.subtitle;
    return html`
      <div class="card">
        ${hasHeader ? html`
          <div class="card-head">
            <div>
              ${this.title ? html`<div class="card-title">${this.title}</div>` : ''}
              ${this.subtitle ? html`<div class="card-sub">${this.subtitle}</div>` : ''}
            </div>
            <slot name="header-actions"></slot>
          </div>
        ` : ''}
        <slot></slot>
      </div>
    `;
  }
}

customElements.define('nebula-card-content', NebulaCardContent);