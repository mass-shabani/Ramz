import { LitElement, html } from '../lit-import.js';

export class CollapseButton extends LitElement {
  createRenderRoot() { return this; }

  _onClick() {
    this.dispatchEvent(new CustomEvent('toggle', {
      bubbles: true,
      composed: true
    }));
  }

  render() {
    return html`
      <div class="sidebar-footer">
        <button class="collapse-btn" type="button" aria-label="Toggle sidebar" @click=${this._onClick}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 17l-5-5 5-5"/>
            <path d="M18 17l-5-5 5-5"/>
          </svg>
          <span class="collapse-text">Collapse Menu</span>
        </button>
      </div>
    `;
  }
}

customElements.define('collapse-button', CollapseButton);