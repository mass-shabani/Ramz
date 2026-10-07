import { LitElement, html, css } from '../lit-import.js';

export class SidebarMenuGroup extends LitElement {
  static properties = {
    label: { type: String }
  };

  constructor() {
    super();
    this.label = '';
  }

  createRenderRoot() { return this; }

  /* static styles commented out — managed globally in style.css */
  /* static styles = css`
    :host { display: block; }
    .nav-section {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 1.3px;
      text-transform: uppercase;
      color: var(--muted, #7b87a1);
      padding: 16px 12px 8px;
      white-space: nowrap;
    }
  `; */

  render() {
    return html`
      ${this.label ? html`<div class="nav-section">${this.label}</div>` : ''}
      <slot></slot>
    `;
  }
}

customElements.define('sidebar-menu-group', SidebarMenuGroup);