import { LitElement, html } from '../lit-import.js';

export class NebulaPromo extends LitElement {
  static properties = {
    title:       { type: String },
    text:        { type: String },
    buttonLabel: { type: String }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.title = 'Upgrade to Pro';
    this.text = 'Unlock advanced AI predictions, unlimited alerts and priority support.';
    this.buttonLabel = 'Upgrade Now';
  }

  _onClick() {
    this.dispatchEvent(new CustomEvent('promo-click', {
      bubbles: true,
      composed: true
    }));
  }

  render() {
    return html`
      <div class="promo">
        <h4>${this.title}</h4>
        <p>${this.text}</p>
        <button type="button" @click=${this._onClick}>${this.buttonLabel}</button>
      </div>
    `;
  }
}

customElements.define('nebula-promo', NebulaPromo);