import { LitElement, html, css } from '../lit-import.js';

export class NebulaSidebar extends LitElement {
  static properties = {
    collapsed: { type: Boolean, reflect: true }
  };

  constructor() {
    super();
    this.collapsed = false;
    this._mobileOpen = false;
  }

  createRenderRoot() { return this; }

  /* static styles commented out — managed globally in style.css */
  /* static styles = css`
    :host {
      display: block;
    }

    .nav {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .nav-section {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 1.3px;
      text-transform: uppercase;
      color: var(--muted, #7b87a1);
      padding: 16px 12px 8px;
      white-space: nowrap;
    }

    .promo {
      position: relative;
      margin: 0 14px 14px;
      padding: 16px;
      border-radius: 16px;
      overflow: hidden;
      background: linear-gradient(135deg, rgba(99,102,241,.24), rgba(168,85,247,.14));
      border: 1px solid rgba(129,140,248,.24);
    }

    .promo::after {
      content: '';
      position: absolute;
      top: -55px;
      right: -45px;
      width: 130px;
      height: 130px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(168,85,247,.5), transparent 70%);
    }

    .promo h4 {
      font-size: 13.5px;
      font-weight: 700;
      margin-bottom: 4px;
      position: relative;
    }

    .promo p {
      font-size: 11.5px;
      line-height: 1.5;
      color: var(--text-dim, #a3aec4);
      margin-bottom: 13px;
      position: relative;
    }

    .promo button {
      position: relative;
      width: 100%;
      height: 36px;
      border: none;
      border-radius: 11px;
      cursor: pointer;
      font-size: 12.5px;
      font-weight: 600;
      color: #fff;
      background: linear-gradient(135deg,#6366f1,#a855f7);
      transition: transform .18s, box-shadow .18s;
    }

    .promo button:hover {
      transform: translateY(-1px);
      box-shadow: 0 12px 26px -10px rgba(129,140,248,1);
    }

    .sidebar-footer {
      flex: 0 0 auto;
      padding: 14px;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    .collapse-btn {
      position: relative;
      width: 100%;
      height: 48px;
      border-radius: 14px;
      cursor: pointer;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      font-size: 13px;
      font-weight: 600;
      color: #c7d2fe;
      background: linear-gradient(135deg, rgba(99,102,241,.22), rgba(168,85,247,.16));
      border: 1px solid rgba(129,140,248,.3);
      transition: background .25s, border-color .25s, color .25s,
                  box-shadow .25s, transform .12s;
    }

    .collapse-btn::before {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(120deg, transparent 30%, rgba(255,255,255,.16) 50%, transparent 70%);
      transform: translateX(-120%);
      transition: transform .6s ease;
    }

    .collapse-btn:hover::before {
      transform: translateX(120%);
    }

    .collapse-btn:hover {
      background: linear-gradient(135deg, rgba(99,102,241,.4), rgba(168,85,247,.3));
      border-color: rgba(129,140,248,.65);
      color: #fff;
      box-shadow: 0 0 0 4px rgba(99,102,241,.1), 0 14px 32px -12px rgba(99,102,241,1);
    }

    .collapse-btn:active {
      transform: scale(.975);
    }

    .collapse-btn svg {
      width: 18px;
      height: 18px;
      flex: 0 0 auto;
      transition: transform .38s cubic-bezier(.4,0,.2,1);
    }

    .collapse-text {
      white-space: nowrap;
      transition: opacity .2s;
    }
  `; */

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
      this.collapsed = !this.collapsed;
      this.classList.toggle('collapsed', this.collapsed);
      const txt = this.querySelector('.collapse-text');
      if (txt) txt.textContent = this.collapsed ? 'Expand Menu' : 'Collapse Menu';
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
