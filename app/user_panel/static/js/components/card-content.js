import { LitElement, html, css } from '../lit-import.js';

export class NebulaCardContent extends LitElement {
  static properties = {
    title:    { type: String },
    subtitle: { type: String }
  };

  constructor() {
    super();
    this.title = '';
    this.subtitle = '';
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

    .card-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 22px;
      flex-wrap: wrap;
    }

    .card-title {
      font-size: 15px;
      font-weight: 700;
    }

    .card-sub {
      font-size: 11.5px;
      color: var(--muted);
      margin-top: 5px;
    }
  `; */

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
