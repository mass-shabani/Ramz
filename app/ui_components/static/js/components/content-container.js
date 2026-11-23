import { defineComponent, attr, emit } from '../_base.js';

/**
 * <content-container>
 *
 * Loads HTML fragments via POST and injects them into a dedicated
 * child element. The container itself never holds the content directly,
 * so the loading and error overlays can coexist with it.
 *
 * Attributes:
 *   • initial-endpoint — URL to load automatically on connect
 *   • method           — "POST" (default) or "GET"
 *
 * Public API:
 *   • load(url)        — fetch and inject a fragment
 *   • reload()         — re-fetch the last URL
 *   • clear()          — empty the container
 *   • setInitialEndpoint(url) — change the fallback URL
 *
 * Listens to:
 *   • ramz:load-content — { url, label } from menu items
 *
 * Emits:
 *   • ramz:content-loaded  — { url }
 *   • ramz:content-error   — { url, status }
 */
class ContentContainer extends HTMLElement {
  #refs         = {};
  #lastUrl      = '';
  #loading      = false;
  #abortCtrl    = null;
  #scriptsMap   = {};

  static get observedAttributes() {
    return ['initial-endpoint', 'method'];
  }

  connectedCallback() {
    this._render();
    this._cacheRefs();
    this._attachListeners();

    // Parse the scripts-map attribute (JSON: urlPath → [scriptSrc]).
    // A malformed value falls back to {} so partials without client
    // JS keep working unchanged.
    try {
      const raw = this.getAttribute('scripts-map') || '';
      this.#scriptsMap = raw ? JSON.parse(raw) : {};
    } catch (err) {
      console.warn('[content-container] invalid scripts-map:', err);
      this.#scriptsMap = {};
    }

    const initial = attr(this, 'initial-endpoint', '');
    if (initial) {
      // Defer to let the rest of the panel render first
      queueMicrotask(() => this.load(initial));
    }
  }

  disconnectedCallback() {
    this._detachListeners();
    if (this.#abortCtrl) this.#abortCtrl.abort();
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal) return;
    // No automatic reload on attribute change — the app controls when to load
  }

  /* --------------------------------------------------------------
     Public API
     -------------------------------------------------------------- */
  async load(url) {
    if (!url) return;
    if (this.#loading) {
      this.#abortCtrl?.abort();
    }

    this.#lastUrl = url;
    this.#loading = true;
    this._setState('loading');
    emit(this, 'ramz:content-loading', { url });

    const method = attr(this, 'method', 'POST').toUpperCase();
    const ctrl   = new AbortController();
    this.#abortCtrl = ctrl;

    try {
      const resp = await fetch(url, {
        method,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'text/html'
        },
        credentials: 'same-origin',
        signal: ctrl.signal
      });

      if (!resp.ok) {
        throw Object.assign(new Error('HTTP ' + resp.status), { status: resp.status });
      }

      const html = await resp.text();

      // Guard: if another load happened while we were waiting, discard
      if (this.#abortCtrl !== ctrl) return;

      this.#refs.content.innerHTML = html;

      // Load scripts registered for this URL via ComponentService's
      // scripts-map. This replaces innerHTML <script> execution with
      // explicit <script src> injection so the browser handles fetch +
      // execution reliably and per partials.
      try {
        await this._loadScriptsForUrl(url);
      } catch (err) {
        // Per-script errors are caught individually; this catch is
        // a last-resort safety net so a single failure never blocks
        // the container from reaching the ready state.
        console.error(
          '[content-container] _loadScriptsForUrl crashed:', err
        );
      }

      this._setState('ready');
      emit(this, 'ramz:content-loaded', { url });

      // Scroll the container's top into view on change
      this.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
      if (err.name === 'AbortError') return;
      if (this.#abortCtrl !== ctrl) return;

      this._setState('error', err.status);
      emit(this, 'ramz:content-error', { url, status: err.status });
      // eslint-disable-next-line no-console
      console.error('[content-container] load failed:', err);

    } finally {
      if (this.#abortCtrl === ctrl) {
        this.#loading = false;
        this.#abortCtrl = null;
      }
    }
  }

  reload() {
    if (this.#lastUrl) return this.load(this.#lastUrl);
  }

  clear() {
    this.#refs.content.innerHTML = '';
    this._setState('idle');
  }

  setInitialEndpoint(url) {
    if (url) this.setAttribute('initial-endpoint', url);
    else     this.removeAttribute('initial-endpoint');
  }

  /* --------------------------------------------------------------
     Shell
     -------------------------------------------------------------- */
  _render() {
    this.innerHTML = `
      <div class="content-stage">
        <div class="content-loading" aria-hidden="true">
          <span class="content-spinner"></span>
        </div>

        <div class="content-error" role="alert">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9"/>
            <path d="M12 8v5"/>
            <path d="M12 16h.01"/>
          </svg>
          <div class="content-error-text">
            <strong>Failed to load content</strong>
            <span>Please check your connection and try again.</span>
          </div>
          <button class="content-retry" type="button">Retry</button>
        </div>

        <div class="content-inner"></div>
      </div>
    `;
  }

  _cacheRefs() {
    this.#refs = {
      stage:   this.querySelector('.content-stage'),
      content: this.querySelector('.content-inner'),
      retry:   this.querySelector('.content-retry')
    };
  }

  _setState(state, status) {
    this.#refs.stage.dataset.state = state;
    this.setAttribute('aria-busy', String(state === 'loading'));

    if (state === 'error' && status) {
      this.#refs.stage.dataset.errorCode = String(status);
    } else if (state !== 'error') {
      delete this.#refs.stage.dataset.errorCode;
    }
  }

  /* --------------------------------------------------------------
     Listeners
     -------------------------------------------------------------- */
  _attachListeners() {
    window.addEventListener('ramz:load-content', this._onLoadRequest);
    this.#refs.retry?.addEventListener('click', this._onRetry);
  }

  _detachListeners() {
    window.removeEventListener('ramz:load-content', this._onLoadRequest);
    this.#refs.retry?.removeEventListener('click', this._onRetry);
  }

  _onLoadRequest = (e) => {
    const url = e.detail?.url;
    if (url) this.load(url);
  };

  _onRetry = () => {
    this.reload();
  };

  /* --------------------------------------------------------------
      Script loading (scripts-map)
      -------------------------------------------------------------- */

  /**
   * Load the scripts registered for `url` via ComponentService.
   *
   * Why this instead of executing <script> tags found inside the
   * partial?
   *   1. HTML5 marks <script> elements inserted via innerHTML as
   *      "already started" — they never execute.
   *   2. fetch + eval is brittle (CSP, cross-browser timing, error
   *      attribution) and hides failures from the user.
   *   3. The rest of Ramz already keeps JS in the parent page
   *      (settings.html, admin_layout.html). This method brings
   *      partial-only JS into the same mental model: the module
   *      declares its scripts, the container loads them explicitly
   *      from <head>, and the browser handles fetch + execution.
   *
   * URL normalization:
   *   The map keys are pathnames (e.g. "/crypto/coins/partials/list").
   *   We strip query/hash from the loaded URL before lookup so that
   *   cache-busting query strings do not break matching.
   *
   * Idempotency:
   *   Each navigation creates a fresh <script src> element and
   *   removes it after load. The browser's HTTP cache serves the
   *   body; execution happens every time, which is what partials
   *   with DOM-binding initializers need (e.g. coins_settings.js).
   */
  async _loadScriptsForUrl(url) {
    if (!url || !this.#scriptsMap) return;

    let pathname;
    try {
      pathname = new URL(url, window.location.origin).pathname;
    } catch (err) {
      pathname = url;
    }

    const scripts = this.#scriptsMap[pathname];
    if (!Array.isArray(scripts) || scripts.length === 0) return;

    // Strictly sequential: a partial's initializer may depend on
    // a shared helper registered by an earlier script.
    for (const src of scripts) {
      try {
        await this._loadScript(src);
      } catch (err) {
        console.error(
          `[content-container] script load failed: ${src}`, err
        );
      }
    }
  }

  /**
   * Inject a single <script src> into <head>, await load, then
   * remove it. Rejection propagates to the caller so a failure is
   * attributed to the specific src.
   */
  _loadScript(src) {
    return new Promise((resolve, reject) => {
      const el = document.createElement('script');
      el.src = src;
      el.async = false;
      el.onload = () => {
        el.remove();
        resolve();
      };
      el.onerror = () => {
        el.remove();
        reject(new Error(`Failed to load ${src}`));
      };
      document.head.appendChild(el);
    });
  }
}

defineComponent('content-container', ContentContainer);