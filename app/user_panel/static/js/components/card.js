import { LitElement, html, css } from '../lit-import.js';

export class NebulaCard extends LitElement {
  createRenderRoot() { return this; }

  /* static styles commented out — managed globally in style.css */
  /* static styles = css`
    :host { display: block; }
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
  `; */

  render() {
    return html`<div class="card"><slot></slot></div>`;
  }
}

customElements.define('nebula-card', NebulaCard);
