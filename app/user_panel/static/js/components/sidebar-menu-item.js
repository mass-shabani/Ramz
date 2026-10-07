import { LitElement, html, css } from '../lit-import.js';

export class SidebarMenuItem extends LitElement {
  static properties = {
    label: { type: String },
    href: { type: String },
    active: { type: Boolean },
    badge: { type: String },
    badgeVariant: { type: String }
  };

  constructor() {
    super();
    this.label = '';
    this.href = '#';
    this.active = false;
    this.badge = '';
    this.badgeVariant = '';
  }

  createRenderRoot() { return this; }

  /* static styles commented out — managed globally in style.css */
  /* static styles = css`
    :host {
      display: block;
    }

    .nav-item {
      position: relative;
      display: flex;
      align-items: center;
      gap: 13px;
      height: 46px;
      padding: 0 13px;
      border-radius: 13px;
      color: var(--text-dim);
      font-size: 14px;
      font-weight: 500;
      white-space: nowrap;
      text-decoration: none;
      transition: background .18s, color .18s;
    }

    .nav-item:hover {
      background: rgba(255,255,255,.05);
      color: var(--text);
    }

    .nav-item.active {
      background: linear-gradient(90deg, rgba(99,102,241,.28), rgba(99,102,241,.06));
      color: #fff;
      font-weight: 600;
    }

    .nav-item.active::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 22px;
      border-radius: 0 3px 3px 0;
      background: linear-gradient(180deg,#818cf8,#a855f7);
      box-shadow: 0 0 14px rgba(129,140,248,.95);
    }

    .nav-icon {
      width: 20px;
      height: 20px;
      flex: 0 0 auto;
      display: grid;
      place-items: center;
    }

    .nav-icon svg {
      width: 19px;
      height: 19px;
    }

    .nav-text {
      flex: 1 1 auto;
      min-width: 0;
    }

    .nav-badge {
      margin-left: auto;
      font-size: 10.5px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(99,102,241,.24);
      color: #a5b4fc;
      white-space: nowrap;
    }

    .nav-badge.danger {
      background: rgba(244,63,94,.2);
      color: #fda4af;
    }
  `; */

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
