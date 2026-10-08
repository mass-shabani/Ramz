import { defineComponent, attr } from '../_base.js';

/**
 * <ramz-brand>
 *
 * Attributes:
 *   • name      — brand name (default: "Nebula")
 *   • subtitle  — brand subtitle (default: "Admin Suite")
 *
 * Renders the standard brand block used in the sidebar and login card.
 * The logo SVG is embedded as a string and rendered once at connect time.
 */
class RamzBrand extends HTMLElement {
  static get observedAttributes() {
    return ['name', 'subtitle'];
  }

  connectedCallback() {
    this._render();
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal !== newVal && this.isConnected) {
      this._render();
    }
  }

  _render() {
    const name     = attr(this, 'name', 'Nebula');
    const subtitle = attr(this, 'subtitle', 'Admin Suite');

    this.innerHTML = `
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
          <span class="brand-name">${name}</span>
          <span class="brand-sub">${subtitle}</span>
        </div>
      </div>
    `;
  }
}

defineComponent('ramz-brand', RamzBrand);