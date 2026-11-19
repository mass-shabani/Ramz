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

      // Per HTML5 spec, <script> elements inserted via innerHTML are
      // marked "already started" and never execute. To support
      // partials with client-side JS, we fetch each script's source
      // and execute it explicitly (see _executeScripts for details).
      //
      // Awaiting here means `ramz:content-loaded` fires only AFTER
      // all scripts have finished running — so any listener can rely
      // on the partial being fully wired. Partials with no <script>
      // resolve immediately (early return in _executeScripts).
      try {
        await this._executeScripts(this.#refs.content);
      } catch (err) {
        // _executeScripts catches per-script errors itself; this
        // catch is a last-resort safety net so a single failure
        // never blocks the container from reaching the ready state.
        console.error(
          '[content-container] _executeScripts crashed:', err
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
     Script execution (explicit fetch + eval)
     -------------------------------------------------------------- */

  /**
   * Execute every <script> element inside `container`.
   *
   * Why explicit fetch + eval instead of re-injection?
   *   Per HTML5 spec, <script> elements inserted via innerHTML are
   *   marked "already started" and never execute. Replacing them
   *   with a fresh <script> via replaceChild works in some browsers
   *   but is NOT reliable across Chrome and other engines (verified
   *   empirically in this project). The only reliable cross-browser
   *   approach is to fetch the source text ourselves and execute it
   *   explicitly.
   *
   * Execution model:
   *   • External classic scripts: fetch text, then `(0, eval)(text)`.
   *     Indirect eval runs the code in the global scope, exactly
   *     like a real <script> tag would (access to window, document,
   *     fetch, ...).
   *   • External module scripts (`type="module"`): fetch text,
   *     create a Blob URL, and `await import(blobUrl)`. This is the
   *     standard way to run ES module source at runtime.
   *   • Inline scripts (classic or module): same as above, using
   *     the inline textContent instead of a network fetch.
   *
   * Ordering:
   *   Scripts execute strictly in document order. For external
   *   scripts, each fetch is awaited before the next script runs.
   *
   * Errors:
   *   Any fetch/parse/runtime error is caught per-script and logged
   *   via console.error with the script's src (or "<inline>") so it
   *   is easy to attribute. Execution continues to the next script.
   *
   * Backward compatibility:
   *   Partials with zero <script> tags are a no-op (early return).
   *   The whole method is async; callers await it so that
   *   `ramz:content-loaded` fires only AFTER all scripts have run.
   *
   * Security note:
   *   `(0, eval)` requires no CSP `'unsafe-eval'` for this project
   *   because the FastAPI app does not set a Content-Security-Policy
   *   header. The scripts being eval'd are served from the same
   *   origin (/static/crypto_coins/...). If a CSP is ever added,
   *   switch the classic branch to Blob + Function or Blob + import
   *   with `script-src blob:` (see git history for the rationale).
   */
  async _executeScripts(container) {
    if (!container) return;

    const scripts = Array.from(container.querySelectorAll('script'));
    if (scripts.length === 0) return;

    console.debug(
      `[content-container] executing ${scripts.length} script(s)`
    );

    for (const oldScript of scripts) {
      const src = oldScript.getAttribute('src');
      const textContent = oldScript.textContent || '';
      const isModule = oldScript.getAttribute('type') === 'module';
      const label = src || '<inline>';

      // Remove from DOM — we execute manually. Keeping it would also
      // be harmless, but removing avoids the (non-functional)
      // "already started" script from confusing DevTools' Elements
      // panel.
      oldScript.remove();

      try {
        let code;
        if (src) {
          const r = await fetch(src, { credentials: 'same-origin' });
          if (!r.ok) {
            throw new Error(`HTTP ${r.status} for ${src}`);
          }
          code = await r.text();
        } else {
          code = textContent;
        }

        if (isModule) {
          // ES module source must go through import(). Blob URL is
          // the standard mechanism at runtime.
          const blob = new Blob(
            [code], { type: 'application/javascript' }
          );
          const url = URL.createObjectURL(blob);
          try {
            await import(url);
          } finally {
            URL.revokeObjectURL(url);
          }
        } else {
          // Classic script — indirect eval runs it in the global
          // scope (equivalent to a real <script> tag).
          (0, eval)(code);
        }

        console.debug(
          `[content-container] executed: ${label}`
        );
      } catch (err) {
        console.error(
          `[content-container] script failed: ${label}`, err
        );
      }
    }
  }
}

defineComponent('content-container', ContentContainer);