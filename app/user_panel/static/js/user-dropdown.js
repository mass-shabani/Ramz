/**
 * App User Dropdown - A Lit web component for the user dropdown menu in the navbar.
 * Shows avatar, username, and a dropdown menu with profile/settings/logout options.
 */
import { LitElement, html, css, nothing } from '/static/js/vendor/lit-all.min.js';

class AppUserDropdown extends LitElement {
    static properties = {
        username: { type: String },
        avatar: { type: String },
        menuItems: { type: Array },
        open: { type: Boolean, reflect: true }
    };

    constructor() {
        super();
        this.username = 'Guest';
        this.avatar = '👤';
        this.menuItems = [
            { label: 'Profile', icon: '👤', url: '/profile' },
            { label: 'Settings', icon: '⚙️', url: '/settings' },
            { type: 'divider' },
            { label: 'Logout', icon: '🚪', url: '/logout' }
        ];
        this.open = false;
    }

    static styles = css`
        :host {
            display: inline-block;
            position: relative;
        }

        .user-trigger {
            background: var(--surface-bg, #1F2937);
            border: 1px solid var(--border-color, #374151);
            border-radius: 50px;
            padding: 0.5rem 1rem;
            color: var(--text-primary, #F9FAFB);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s ease;
            font-size: 0.9rem;
        }

        .user-trigger:hover {
            background: var(--accent, #F59E0B);
            color: var(--primary-bg, #0B1120);
        }

        .user-avatar {
            font-size: 1.25rem;
        }

        .user-name {
            font-weight: 500;
        }

        .dropdown-icon {
            font-size: 0.7rem;
            transition: transform 0.2s ease;
        }

        :host([open]) .dropdown-icon {
            transform: rotate(180deg);
        }

        .user-menu {
            position: absolute;
            top: calc(100% + 5px);
            right: 0;
            background: var(--surface-bg, #1F2937);
            border: 1px solid var(--border-color, #374151);
            border-radius: var(--border-radius, 8px);
            min-width: 200px;
            padding: 0.5rem 0;
            opacity: 0;
            visibility: hidden;
            transform: translateY(-10px);
            transition: all 0.2s ease;
            z-index: 1000;
            box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1));
        }

        :host([open]) .user-menu {
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }

        .user-menu-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            color: var(--text-secondary, #9CA3AF);
            font-size: 0.9rem;
            transition: all 0.2s ease;
            text-decoration: none;
            cursor: pointer;
        }

        .user-menu-item:hover {
            background: var(--accent, #F59E0B);
            color: var(--primary-bg, #0B1120);
        }

        .user-menu-divider {
            border: none;
            border-top: 1px solid var(--border-color, #374151);
            margin: 0.25rem 0;
        }

        .user-menu-item-icon {
            font-size: 1rem;
        }
    `;

    render() {
        return html`
            <button class="user-trigger" @click=${this._toggle}>
                <span class="user-avatar">${this.avatar}</span>
                <span class="user-name">${this.username}</span>
                <span class="dropdown-icon">▼</span>
            </button>
            <div class="user-menu">
                ${this.menuItems.map(item => 
                    item.type === 'divider'
                        ? html`<hr class="user-menu-divider">`
                        : html`
                            <a 
                                href="${item.url}" 
                                class="user-menu-item"
                                @click=${(e) => this._onItemClick(e, item)}
                            >
                                <span class="user-menu-item-icon">${item.icon}</span>
                                <span>${item.label}</span>
                            </a>
                        `
                )}
            </div>
        `;
    }

    _toggle(event) {
        event.stopPropagation();
        this.open = !this.open;
        if (this.open) {
            this._setupOutsideClick();
        }
    }

    _onItemClick(event, item) {
        event.stopPropagation();
        this.open = false;
        if (item.action && typeof item.action === 'function') {
            item.action(event, item);
        }
    }

    _setupOutsideClick() {
        const handleClick = (e) => {
            if (!this.contains(e.target)) {
                this.open = false;
                document.removeEventListener('click', handleClick);
            }
        };
        document.addEventListener('click', handleClick, { once: false });
    }
}

customElements.define('app-user-dropdown', AppUserDropdown);
