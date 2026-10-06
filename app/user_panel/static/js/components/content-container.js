import { LitElement, html } from '../lit-import.js';

export class ContentContainer extends LitElement {
  static properties = {
    initialEndpoint: { type: String },
    _loading: { state: true }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.initialEndpoint = '';
    this._loading = false;
  }

  connectedCallback() {
    super.connectedCallback();
    if (this.initialEndpoint) {
      this._load(this.initialEndpoint);
    }
  }

  async _load(endpoint) {
    this._loading = true;
    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Accept': 'text/html' }
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const html = await resp.text();
      this.innerHTML = `<div class="content-container">${html}</div>`;
    } catch (e) {
      this.innerHTML = `<div class="card"><p>Failed to load content.</p></div>`;
    } finally {
      this._loading = false;
    }
  }

  render() {
    return html`<slot></slot>`;
  }
}

customElements.define('content-container', ContentContainer);