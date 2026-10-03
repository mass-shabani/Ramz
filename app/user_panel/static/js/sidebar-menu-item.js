/**
 * Sidebar Menu Item - A Lit web component for individual sidebar menu entries.
 * Supports tooltip display on hover and dual-action callbacks:
 * - on_action: triggered on click/tap
 * - on_over_action: triggered on mouse enter/leave
 */
import { LitElement, html, css } from '/static/js/vendor/lit-all.min.js';

class SidebarMenuItem extends LitElement {
    static properties = {
        item: { type: Object },
        collapsed: { type: Boolean, reflect: true },
        active: { type: Boolean, reflect: true }
    };

    constructor() {
        super();
        this.item = {};
        this.collapsed = false;
        this.active = false;
    }

    static styles = css`
        :host {
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
            cursor: pointer;
            direction: rtl;
            position: relative;
            border: none;
            background: none;
            width: 100%;
            text-align: right;
        }

        :host(:hover) {
            color: var(--text-primary, #F9FAFB);
        }

        :host([active]) {
            background: rgba(245, 158, 11, 0.1);
            color: var(--accent, #F59E0B);
            border-left: 3px solid var(--accent, #F59E0B);
        }

        .icon {
            font-size: 1.25rem;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
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

        :host([collapsed]) {
            justify-content: center;
            padding: 0.875rem;
        }

        .tooltip {
            position: absolute;
            left: 100%;
            top: 50%;
            transform: translateY(-50%);
            background: var(--surface-bg, #1F2937);
            color: var(--text-primary, #F9FAFB);
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            white-space: nowrap;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.2s, visibility 0.2s;
            pointer-events: none;
            z-index: 1000;
            border: 1px solid var(--border-color, #374151);
        }

        :host([collapsed]):hover .tooltip {
            opacity: 1;
            visibility: visible;
        }

        .menu-item {
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
            width: 100%;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 1rem;
            color: inherit;
            font: inherit;
        }
    `;

    render() {
        const { icon, label, tooltip, action } = this.item || {};
        return html`
            <button
                class="menu-item"
                @click=${this._handleClick}
                @mouseenter=${this._handleMouseEnter}
                @mouseleave=${this._handleMouseLeave}
            >
                <span class="icon">${icon || '🔗'}</span>
                <span class="label">${label || ''}</span>
                ${tooltip ? html`<span class="tooltip">${tooltip}</span>` : ''}
            </button>
        `;
    }

    _handleClick(event) {
        const { action } = this.item || {};
        if (action && typeof action.on_action === 'function') {
            event.preventDefault();
            event.stopPropagation();
            action.on_action(event, this.item);
        }
    }

    _handleMouseEnter(event) {
        const { action } = this.item || {};
        if (action && typeof action.on_over_action === 'function') {
            event.preventDefault();
            action.on_over_action(event, this.item);
        }
    }

    _handleMouseLeave(event) {
        const { action } = this.item || {};
        if (action && typeof action.on_over_action === 'function') {
            event.preventDefault();
        }
    }
}

customElements.define('sidebar-menu-item', SidebarMenuItem);
