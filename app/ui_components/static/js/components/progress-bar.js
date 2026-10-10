import { defineComponent } from '../_base.js';

/**
 * <ramz-progress-bar>
 *
 * A thin, glowing progress bar used to indicate AJAX loading. By default
 * it listens to the global content-loading events emitted by
 * <content-container> and animates automatically. Auto-mode can be
 * disabled with the `auto="false"` attribute to allow manual control.
 *
 * Attributes:
 *   • auto — "true" (default) or "false". When false, the component
 *            does not listen to global events and must be controlled
 *            via its public API.
 *
 * Public API:
 *   • start()               — begin the progress animation
 *   • done()                — finish and fade out
 *   • reset()               — reset to zero, hide immediately
 *   • setProgress(percent)  — set the bar width to a specific percentage
 */
class RamzProgressBar extends HTMLElement {
  static get observedAttributes() {
    return ['auto'];
  }

  #bar    = null;
  #track  = null;
  #timer  = null;
  #resetTimer = null;
  #autoMode   = null;

  /* --------------------------------------------------------------
     Lifecycle
     -------------------------------------------------------------- */
  connectedCallback() {
    this._render();
    this._cacheRefs();
    this._syncAutoMode();
  }

  disconnectedCallback() {
    this._detachAutoListeners();
    clearTimeout(this.#timer);
    clearTimeout(this.#resetTimer);
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal) return;
    if (name === 'auto') this._syncAutoMode();
  }

  /* --------------------------------------------------------------
     Public API
     -------------------------------------------------------------- */
  start() { this._start(); }
  done()  { this._finish(); }
  reset() { this._reset(); }

  setProgress(percent) {
    if (!this.#bar) return;
    const clamped = Math.max(0, Math.min(100, Number(percent) || 0));
    this.#bar.style.transition = 'width .3s ease';
    this.#bar.style.width = clamped + '%';
  }

  /* --------------------------------------------------------------
     Rendering
     -------------------------------------------------------------- */
  _render() {
    this.innerHTML = `
      <div class="top-progress" aria-hidden="true">
        <div class="top-progress-bar"></div>
      </div>
    `;
  }

  _cacheRefs() {
    this.#track = this.querySelector('.top-progress');
    this.#bar   = this.querySelector('.top-progress-bar');
  }

  /* --------------------------------------------------------------
     Auto-mode wiring
     -------------------------------------------------------------- */
  _syncAutoMode() {
    const attr = this.getAttribute('auto');
    const shouldBeAuto = attr === null || attr === 'true' || attr === '';

    if (shouldBeAuto === this.#autoMode) return;

    this.#autoMode = shouldBeAuto;
    if (shouldBeAuto) {
      this._attachAutoListeners();
    } else {
      this._detachAutoListeners();
    }
  }

  _attachAutoListeners() {
    window.addEventListener('ramz:content-loading', this._onStart);
    window.addEventListener('ramz:content-loaded',  this._onDone);
    window.addEventListener('ramz:content-error',   this._onDone);
  }

  _detachAutoListeners() {
    window.removeEventListener('ramz:content-loading', this._onStart);
    window.removeEventListener('ramz:content-loaded',  this._onDone);
    window.removeEventListener('ramz:content-error',   this._onDone);
  }

  /* --------------------------------------------------------------
     Animation logic
     -------------------------------------------------------------- */
  _start() {
    if (!this.#bar || !this.#track) return;

    clearTimeout(this.#timer);
    clearTimeout(this.#resetTimer);

    // Reset silently so the next transition starts from zero
    this.#bar.style.transition   = 'none';
    this.#bar.style.width        = '0%';
    this.#track.style.transition = 'none';
    this.#track.style.opacity    = '1';

    // Force reflow to re-arm transitions
    void this.#bar.offsetWidth;

    // Restore transitions
    this.#bar.style.transition   = '';
    this.#track.style.transition = '';

    // Kick off
    this.#track.classList.add('is-visible', 'is-running');
    this.#bar.style.width = '85%';
  }

  _finish() {
    if (!this.#bar || !this.#track) return;

    this.#track.classList.remove('is-running');

    // Snap to 100%
    this.#bar.style.transition = 'width .3s ease';
    this.#bar.style.width = '100%';

    // Fade out after the bar reaches the right edge
    this.#timer = setTimeout(() => {
      this.#track.classList.remove('is-visible');
      this.#track.style.opacity = '0';

      // Reset width once the fade-out is complete
      this.#resetTimer = setTimeout(() => {
        this.#bar.style.transition = 'none';
        this.#bar.style.width = '0%';
        void this.#bar.offsetWidth;
        this.#bar.style.transition = '';
      }, 320);
    }, 320);
  }

  _reset() {
    if (!this.#bar || !this.#track) return;

    clearTimeout(this.#timer);
    clearTimeout(this.#resetTimer);

    this.#track.classList.remove('is-visible', 'is-running');
    this.#bar.style.transition = 'none';
    this.#bar.style.width = '0%';
    void this.#bar.offsetWidth;
    this.#bar.style.transition = '';
  }

  /* --------------------------------------------------------------
     Event handlers
     -------------------------------------------------------------- */
  _onStart = () => this._start();
  _onDone  = () => this._finish();
}

defineComponent('ramz-progress-bar', RamzProgressBar);