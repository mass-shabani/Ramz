import { LitElement, html } from '../lit-import.js';

export class NebulaBrand extends LitElement {
  static properties = {
    name:     { type: String },
    subtitle: { type: String }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.name = 'Ramz';
    this.subtitle = 'CRYPTO INTELLIGENCE';
  }

  render() {
    return html`
      <div class="brand">
        <div class="brand-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2 3 7v10l9 5 9-5V7z"/>
            <path d="M12 22V12"/>
            <path d="m3 7 9 5 9-5"/>
          </svg>
        </div>
        <div class="brand-text">
          <span class="brand-name">${this.name}</span>
          <span class="brand-sub">${this.subtitle}</span>
        </div>
      </div>
    `;
  }
}

customElements.define('nebula-brand', NebulaBrand);