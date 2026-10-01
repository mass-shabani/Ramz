/**
 * App Panel Container - A Lit web component for the main panel content area.
 * Supports AJAX loading of content and dynamic content injection.
 * Designed to receive navigation events from the sidebar component.
 */
import { LitElement, html, css, unsafeHTML } from '/static/js/vendor/lit-all.min.js';

class AppPanelContainer extends LitElement {
    static properties = {
        content: { type: String },
        loading: { type: Boolean, reflect: true },
        error: { type: String }
    };

    constructor() {
        super();
        this.content = '';
        this.loading = false;
        this.error = '';
    }

    static styles = css`
        :host {
            display: block;
            flex: 1;
            padding: 2rem;
            overflow-y: auto;
            background: var(--primary-bg, #0B1120);
        }

        .panel-content {
            min-height: 100%;
        }

        .loading-overlay {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 3rem;
            color: var(--text-secondary, #9CA3AF);
        }

        .loading-spinner {
            display: inline-block;
            width: 2rem;
            height: 2rem;
            border: 3px solid var(--border-color, #374151);
            border-top-color: var(--accent, #F59E0B);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        .error-message {
            color: var(--danger, #EF4444);
            padding: 1rem;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: var(--border-radius, 8px);
            margin: 1rem 0;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .content-wrapper {
            animation: fadeIn 0.5s ease;
        }
    `;

    render() {
        if (this.loading) {
            return html`
                <div class="panel-content">
                    <div class="loading-overlay">
                        <div class="loading-spinner"></div>
                    </div>
                </div>
            `;
        }

        if (this.error) {
            return html`
                <div class="panel-content">
                    <div class="error-message">${this.error}</div>
                </div>
            `;
        }

        return html`
            <div class="panel-content">
                <div class="content-wrapper">
                    ${this.content ? unsafeHTML(this.content) : html`<p style="color: var(--text-secondary);">No content loaded.</p>`}
                </div>
            </div>
        `;
    }

    /**
     * Load content from a URL via AJAX.
     * @param {string} url - The URL to fetch content from.
     * @param {Object} options - Fetch options.
     */
    async loadContent(url, options = {}) {
        this.loading = true;
        this.error = '';
        const defaultOptions = {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            this.content = await response.text();
            this.dispatchEvent(new CustomEvent('content-loaded', {
                detail: { url, content: this.content },
                bubbles: true,
                composed: true
            }));
        } catch (err) {
            this.error = err.message || 'Failed to load content';
            this.dispatchEvent(new CustomEvent('content-error', {
                detail: { url, error: this.error },
                bubbles: true,
                composed: true
            }));
        } finally {
            this.loading = false;
        }
    }

    /**
     * Set content directly (HTML string).
     * @param {string} content - HTML string to render.
     */
    setContent(content) {
        this.content = content;
        this.error = '';
    }

    /**
     * Clear current content.
     */
    clearContent() {
        this.content = '';
        this.error = '';
    }

    /**
     * Show loading state.
     */
    showLoading() {
        this.loading = true;
    }

    /**
     * Hide loading state.
     */
    hideLoading() {
        this.loading = false;
    }
}

customElements.define('app-panel-container', AppPanelContainer);

/**
 * Global API for managing panel content from anywhere in the application.
 * Usage:
 *   PanelContent.load('/panel/dashboard');
 *   PanelContent.set('<h1>Hello</h1>');
 *   PanelContent.clear();
 */
window.PanelContentAPI = {
    _container: null,

    _getContainer() {
        if (!this._container) {
            this._container = document.querySelector('app-panel-container');
        }
        return this._container;
    },

    load(url, options) {
        const container = this._getContainer();
        if (container) {
            return container.loadContent(url, options);
        } else {
            console.warn('PanelContentAPI: app-panel-container not found in DOM');
            return Promise.reject(new Error('Panel container not found'));
        }
    },

    set(content) {
        const container = this._getContainer();
        if (container) {
            container.setContent(content);
        }
    },

    clear() {
        const container = this._getContainer();
        if (container) {
            container.clearContent();
        }
    },

    showLoading() {
        const container = this._getContainer();
        if (container) {
            container.showLoading();
        }
    },

    hideLoading() {
        const container = this._getContainer();
        if (container) {
            container.hideLoading();
        }
    }
};
