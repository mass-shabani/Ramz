import { LitElement, html } from '../lit-import.js';

export class HamburgerButton extends LitElement {
  createRenderRoot() { return this; }

  _onClick() {
    const sidebar = document.querySelector('nebula-sidebar');
    sidebar?.open?.();
  }

  render() {
    return html`
      <button class="hamburger-btn" type="button" aria-label="Open menu" @click=${this._onClick}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 7h16"/>
          <path d="M4 12h10"/>
          <path d="M4 17h16"/>
        </svg>
      </button>
    `;
  }
}

customElements.define('hamburger-button', HamburgerButton);