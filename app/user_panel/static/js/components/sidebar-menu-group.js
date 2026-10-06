import { LitElement, html } from '../lit-import.js';

export class SidebarMenuGroup extends LitElement {
  static properties = {
    label: { type: String }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this.label = '';
  }

  render() {
    return html`
      ${this.label ? html`<div class="nav-section">${this.label}</div>` : ''}
      <slot></slot>
    `;
  }
}

customElements.define('sidebar-menu-group', SidebarMenuGroup);