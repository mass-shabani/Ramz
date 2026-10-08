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

  static get observedAttributes() {
    return ['initial-endpoint', 'method'];
  }

  connectedCallback() {
    this._render();
    this._cacheRefs();
    this._attachListeners();

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
}

defineComponent('content-container', ContentContainer);