/**
 * App Sidebar - A collapsible sidebar web component built with Lit.
 * Receives menu items as a property and renders them dynamically using
 * child sidebar-menu-item components.
 * Uses locally hosted Lit library.
 * 
 * Action structure for menu items:
 * {
 *   id: 'dashboard',
 *   label: 'داشبورد',
 *   icon: '🏠',
 *   tooltip: 'میز کار اصلی',
 *   action: {
 *     on_action: (event, item) => { ... },       // Click/tap handler
 *     on_over_action: (event, item) => { ... }    // Mouse hover handler
 *   }
 * }
 */
import { LitElement, html, css } from '/static/js/vendor/lit-all.min.js';
import '/static/user_panel/js/sidebar-menu-item.js';

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
            direction: ltr;
        }

        :host([collapsed]) {
            width: 70px;
        }

        .sidebar-header {
            display: flex;
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
            margin-left: auto;
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
    `;

    render() {
        return html`
            <div class="sidebar-header">
                <button class="toggle-btn" @click=${this._toggle}>
                    ☰
                </button>
            </div>
            <nav class="sidebar-nav">
                ${this.items.map(item => html`
                    <sidebar-menu-item
                        .item=${item}
                        .collapsed=${this.collapsed}
                        .active=${this._isActive(item)}
                    ></sidebar-menu-item>
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

    _isActive(item) {
        return item && item.action && item.action.url === window.location.pathname;
    }

    /**
     * Add a menu item dynamically.
     * @param {Object} item - Menu item configuration with action callbacks.
     */
    addMenuItem(item) {
        if (!item || !item.id) return;
        const existing = this.items.find(i => i.id === item.id);
        if (existing) {
            const index = this.items.indexOf(existing);
            this.items = [...this.items.slice(0, index), item, ...this.items.slice(index + 1)];
        } else {
            this.items = [...this.items, item];
        }
    }

    /**
     * Remove a menu item by id.
     * @param {string} itemId - The id of the menu item to remove.
     */
    removeMenuItem(itemId) {
        this.items = this.items.filter(i => i.id !== itemId);
    }

    /**
     * Check if a menu item exists.
     * @param {string} itemId - The id to check.
     * @returns {boolean}
     */
    hasMenuItem(itemId) {
        return this.items.some(i => i.id === itemId);
    }

    /**
     * Get all current menu items.
     * @returns {Array}
     */
    getMenuItems() {
        return [...this.items];
    }
}

customElements.define('app-sidebar', AppSidebar);

/**
 * Global API for managing sidebar menu items from anywhere in the application.
 * Usage:
 *   SidebarAPI.add({ id: 'test', label: 'Test', icon: '🧪', tooltip: 'Test tooltip', action: { on_action: () => { ... } } });
 *   SidebarAPI.remove('test');
 */
window.SidebarAPI = {
    _sidebar: null,

    _getSidebar() {
        if (!this._sidebar) {
            this._sidebar = document.querySelector('app-sidebar');
        }
        return this._sidebar;
    },

    add(item) {
        const sidebar = this._getSidebar();
        if (sidebar) {
            sidebar.addMenuItem(item);
        } else {
            console.warn('SidebarAPI: app-sidebar not found in DOM');
        }
    },

    remove(itemId) {
        const sidebar = this._getSidebar();
        if (sidebar) {
            sidebar.removeMenuItem(itemId);
        }
    },

    has(itemId) {
        const sidebar = this._getSidebar();
        return sidebar ? sidebar.hasMenuItem(itemId) : false;
    },

    list() {
        const sidebar = this._getSidebar();
        return sidebar ? sidebar.getMenuItems() : [];
    }
};
