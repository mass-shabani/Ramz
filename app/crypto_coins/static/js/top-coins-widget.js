/**
 * top-coins-widget.js — <top-coins-widget> dashboard widget.
 *
 * Scope
 * -----
 *   A compact card showing the top N coins by price (same sort as
 *   the full /crypto/coins list page). Composed of:
 *
 *     <ramz-card title="Top Coins" subtitle="...">
 *       ├─ <button slot="header-actions">Refresh</button>
 *       └─ <ramz-table>
 *
 *   Data comes from POST /crypto/coins/api/summary.
 *
 * Loading model
 * -------------
 *   The script is registered as a content script for the
 *   /panel/dashboard URL via crypto_coins/module.py. When the
 *   dashboard partial loads, content-container injects it, the
 *   custom element is upgraded, and connectedCallback fetches data.
 *
 *   This avoids the pitfalls of embedding <script> inside the
 *   partial (never executes after innerHTML) and avoids
 *   cross-module imports (the widget is self-contained).
 *
 * Attributes
 * ----------
 *   • endpoint  — POST target (default: /crypto/coins/api/summary)
 *   • title     — card title (default: "Top Coins")
 *   • subtitle  — card subtitle (default: "By price (high to low)")
 *   • limit     — number of coins (default: 5; clamped server-side)
 *
 * Public API
 * ----------
 *   • reload()  — re-fetch the summary
 *
 * No dependencies on any framework or Ramz JS module. Pure vanilla.
 */
(function () {
  'use strict';

  if (customElements.get('top-coins-widget')) {
    // Already defined (script re-executed by a prior navigation).
    return;
  }

  const DEFAULT_ENDPOINT = '/crypto/coins/api/summary';
  const DEFAULT_LIMIT    = 5;

  class TopCoinsWidget extends HTMLElement {
    static get observedAttributes() {
      return ['endpoint', 'title', 'subtitle', 'limit'];
    }

    #refs = {};
    #fetching = false;

    connectedCallback() {
      this._render();
      this._attachListeners();
      this.reload();
    }

    disconnectedCallback() {
      this._detachListeners();
    }

    attributeChangedCallback(name, oldVal, newVal) {
      if (oldVal === newVal) return;
      if (!this.isConnected) return;
      // Re-render shell on title/subtitle; reload only on endpoint
      // or limit changes. Changing title alone should not re-fetch.
      if (name === 'title' || name === 'subtitle') {
        this._render();
        this._attachListeners();
      } else if (name === 'endpoint' || name === 'limit') {
        this.reload();
      }
    }

    /* ------------------------------------------------------------
       Public API
       ------------------------------------------------------------ */
    async reload() {
      if (this.#fetching) return;

      const table = this.#refs.table;
      if (!table) return;

      const endpoint =
        this.getAttribute('endpoint') || DEFAULT_ENDPOINT;
      const limit =
        parseInt(this.getAttribute('limit') || '', 10) ||
        DEFAULT_LIMIT;

      this.#fetching = true;
      if (typeof table.setLoading === 'function') {
        table.setLoading(true);
      }

      try {
        const r = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type':     'application/json',
            'Accept':           'application/json',
            'X-Requested-With': 'XMLHttpRequest',
          },
          credentials: 'same-origin',
          body: JSON.stringify({ limit: limit }),
        });
        if (!r.ok) throw new Error('HTTP ' + r.status);

        const data = await r.json();
        if (data && data.status === 'success') {
          if (
            typeof table.setColumns === 'function' &&
            Array.isArray(data.columns)
          ) {
            table.setColumns(data.columns);
          }
          if (typeof table.setData === 'function') {
            table.setData(data.rows || []);
          }
        } else {
          if (window.console && console.warn) {
            console.warn(
              '[top-coins-widget] summary rejected:', data
            );
          }
        }
      } catch (err) {
        if (window.console && console.error) {
          console.error(
            '[top-coins-widget] load failed:', err
          );
        }
      } finally {
        this.#fetching = false;
        if (
          this.#refs.table &&
          typeof this.#refs.table.setLoading === 'function'
        ) {
          this.#refs.table.setLoading(false);
        }
      }
    }

    /* ------------------------------------------------------------
       Shell
       ------------------------------------------------------------ */
    _render() {
      const title =
        this.getAttribute('title') || 'Top Coins';
      const subtitle =
        this.getAttribute('subtitle') ||
        'By price (high to low)';

      this.innerHTML = '';

      const card = document.createElement('ramz-card');
      card.setAttribute('title', title);
      card.setAttribute('subtitle', subtitle);

      const refreshBtn = document.createElement('button');
      refreshBtn.type = 'button';
      refreshBtn.className = 'btn-ghost';
      refreshBtn.setAttribute('slot', 'header-actions');
      refreshBtn.setAttribute('data-action', 'refresh');
      refreshBtn.setAttribute('aria-label', 'Refresh top coins');
      refreshBtn.style.cssText =
        'height: 32px; padding: 0 10px; border-radius: 8px; ' +
        'font-size: 11.5px; display: inline-flex; ' +
        'align-items: center; gap: 4px;';
      refreshBtn.textContent = 'Refresh';
      card.appendChild(refreshBtn);

      const table = document.createElement('ramz-table');
      table.setAttribute('empty-text', 'No coins available yet.');
      card.appendChild(table);

      this.appendChild(card);

      this.#refs.card = card;
      this.#refs.table = table;
      this.#refs.refresh = refreshBtn;
    }

    /* ------------------------------------------------------------
       Listeners
       ------------------------------------------------------------ */
    _attachListeners() {
      this.addEventListener('click', this._onClick);
    }

    _detachListeners() {
      this.removeEventListener('click', this._onClick);
    }

    _onClick = (e) => {
      const btn = e.target.closest('[data-action="refresh"]');
      if (btn && this.contains(btn)) {
        this.reload();
      }
    };
  }

  customElements.define('top-coins-widget', TopCoinsWidget);
})();
