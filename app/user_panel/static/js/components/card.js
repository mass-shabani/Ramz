import { LitElement, html } from '../lit-import.js';

export class NebulaCard extends LitElement {
  createRenderRoot() { return this; }

  render() {
    return html`<div class="card"><slot></slot></div>`;
  }
}

customElements.define('nebula-card', NebulaCard);