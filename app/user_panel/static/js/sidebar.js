/**
 * App Sidebar - A collapsible sidebar web component built with Lit.
 * Receives menu items as a property and renders them dynamically.
 */
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/gh/lit/dist@2/all/lit-all.min.js';

class AppSidebar extends LitElement {
    static properties = {
        items: { type: Array },
        collapsed: { type: Boolean, reflect: true }
    };

    constructor() {
        super();
        this.items = [];
        this.collapsed = false;
    }

    static styles = css`
        :host {
            display: block;
            width: 260px;
            transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            background: var(--secondary-bg, #111827);
            border-left: 1px solid var(--border-color, #374151);
            height: 100vh;
            position: sticky;
            top: 0;
            overflow-y: auto;
            overflow-x: hidden;
            direction: rtl;
        }

        :host([collapsed]) {
            width: 70px;
        }

        .sidebar-header {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 1.5rem 1rem;
            border-bottom: 1px solid var(--border-color, #374151);
        }

        .toggle-btn {
            background: transparent;
            border: none;
            color: var(--text-primary, #F9FAFB);
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.5rem;
            border-radius: 8px;
            transition: background 0.2s;
        }

        .toggle-btn:hover {
            background: var(--surface-bg, #1F2937);
        }

        .sidebar-nav {
            display: flex;
            flex-direction: column;
            padding: 1rem 0.5rem;
            gap: 0.5rem;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.875rem 1rem;
            color: var(--text-secondary, #9CA3AF);
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.2s ease;
            white-space: nowrap;
            overflow: hidden;
        }

        .nav-item:hover {
            background: var(--surface-bg, #1F2937);
            color: var(--text-primary, #F9FAFB);
        }

        .nav-item.active {
            background: rgba(245, 158, 11, 0.1);
            color: var(--accent, #F59E0B);
            border-right: 3px solid var(--accent, #F59E0B);
        }

        .icon {
            font-size: 1.25rem;
            flex-shrink: 0;
        }

        .label {
            font-weight: 500;
            font-size: 0.95rem;
            opacity: 1;
            transition: opacity 0.2s;
        }

        :host([collapsed]) .label {
            opacity: 0;
            width: 0;
        }

        :host([collapsed]) .nav-item {
            justify-content: center;
            padding: 0.875rem;
        }
    `;

    render() {
        return html`
            <div class="sidebar-header">
                <button class="toggle-btn" @click=${this._toggle} title="Collapse/Expand Menu">
                    ☰
                </button>
            </div>
            <nav class="sidebar-nav">
                ${this.items.map(item => html`
                    <a 
                        href="${item.url}" 
                        class="nav-item ${this._isActive(item.url) ? 'active' : ''}" 
                        title="${item.tooltip || item.label}"
                    >
                        <span class="icon">${item.icon || '🔗'}</span>
                        <span class="label">${item.label}</span>
                    </a>
                `)}
            </nav>
        `;
    }

    _toggle() {
        this.collapsed = !this.collapsed;
        this.dispatchEvent(new CustomEvent('sidebar-toggle', { 
            detail: { collapsed: this.collapsed },
            bubbles: true,
            composed: true
        }));
    }

    _isActive(url) {
        return window.location.pathname === url;
    }
}

customElements.define('app-sidebar', AppSidebar);