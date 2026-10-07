import { LitElement, html, css, unsafeHTML } from '../lit-import.js';

export class ContentContainer extends LitElement {
  static properties = {
    initialEndpoint: { type: String, attribute: 'initial-endpoint' },
    _content: { state: true },
    _error: { state: true }
  };

  /* static styles commented out — managed globally in style.css */
  /* static styles = css`
    :host { display: block; }
  `; */

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.initialEndpoint = '';
    this._content = '';
    this._error = '';
  }

  connectedCallback() {
    super.connectedCallback();
    if (this.initialEndpoint && !this._content) {
      this._load(this.initialEndpoint);
    }
  }

  async _load(endpoint) {
    this._error = '';
    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Accept': 'text/html' },
        credentials: 'same-origin'
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status} ${resp.statusText}`);
      this._content = await resp.text();
    } catch (e) {
      this._error = `Failed to load content: ${e.message}`;
    }
  }

  render() {
    if (this._error) {
      return html`<div class="card"><p>${this._error}</p></div>`;
    }
    if (!this._content) {
      return html`<div class="card"><p>Loading...</p></div>`;
    }
    return html`${unsafeHTML(this._content)}`;
  }
}

customElements.define('content-container', ContentContainer);
