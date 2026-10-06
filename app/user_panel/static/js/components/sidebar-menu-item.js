import { LitElement, html, css } from '../lit-import.js';

export class SidebarMenuItem extends LitElement {
  static properties = {
    label: { type: String },
    href: { type: String },
    active: { type: Boolean },
    badge: { type: String },
    badgeVariant: { type: String }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.label = '';
    this.href = '#';
    this.active = false;
    this.badge = '';
    this.badgeVariant = '';
  }

  static styles = css`
    :host { display: block; }
  `;

  render() {
    const normalizedVariant = (this.badgeVariant || '').toLowerCase();
    const isDanger = ['danger', 'error'].includes(normalizedVariant) ||
                     ['danger', 'error'].includes(String(this.badge).toLowerCase());
    const badgeClass = this.badge
      ? `nav-badge${isDanger ? ' danger' : ''}`
      : '';

    return html`
      <a class="nav-item${this.active ? ' active' : ''}"
         href="${this.href}"
         title="${this.label}">
        <span class="nav-icon"><slot name="icon"></slot></span>
        <span class="nav-text">${this.label}</span>
        ${this.badge ? html`<span class="${badgeClass}">${this.badge}</span>` : ''}
      </a>
    `;
  }
}

customElements.define('sidebar-menu-item', SidebarMenuItem);
