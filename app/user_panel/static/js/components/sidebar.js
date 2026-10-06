import { LitElement, html } from '../lit-import.js';

export class NebulaSidebar extends LitElement {
  createRenderRoot() { return this; }

  constructor() {
    super();
    this._collapsed = false;
    this._mobileOpen = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this.classList.add('sidebar');
    if (!this.id) this.id = 'sidebar';
    this.addEventListener('toggle', this._onToggle);
  }

  disconnectedCallback() {
    this.removeEventListener('toggle', this._onToggle);
    super.disconnectedCallback();
  }

  _onToggle = () => {
    if (window.innerWidth < 1024) {
      this._mobileOpen ? this.close() : this.open();
    } else {
      this._collapsed = !this._collapsed;
      this.classList.toggle('collapsed', this._collapsed);
      const txt = this.querySelector('.collapse-text');
      if (txt) txt.textContent = this._collapsed ? 'Expand Menu' : 'Collapse Menu';
    }
  };

  open() {
    this.classList.add('mobile-open');
    document.getElementById('overlay')?.classList.add('show');
    document.body.classList.add('no-scroll');
    this._mobileOpen = true;
  }

  close() {
    this.classList.remove('mobile-open');
    document.getElementById('overlay')?.classList.remove('show');
    document.body.classList.remove('no-scroll');
    this._mobileOpen = false;
  }

  render() {
    return html`
      <slot name="brand"></slot>
      <nav class="nav"><slot></slot></nav>
      <slot name="promo"></slot>
      <slot name="footer"></slot>
    `;
  }
}

customElements.define('nebula-sidebar', NebulaSidebar);