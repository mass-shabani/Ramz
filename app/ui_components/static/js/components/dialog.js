import { defineComponent } from '../_base.js';

/**
 * <ramz-dialog>
 *
 * Promise-based modal dialog for confirmations, choices, and messages.
 *
 * Public API:
 *   • ask({...})                     -> Promise<string>       (button value)
 *   • confirm({...})                 -> Promise<bool>
 *   • alert({...})                   -> Promise<void>
 *   • passwordConfirm({...})         -> Promise<string|null>  (password or null)
 *
 * Only one dialog can be open at a time.
 */
class RamzDialog extends HTMLElement {
  #resolver = null;
  #busy = false;
  #refs = {};
  #cancelValue = 'cancel';
  #passwordInput = null;

  connectedCallback() {
    this._render();
    this._cacheRefs();
    this._attachListeners();
  }

  disconnectedCallback() {
    this._detachListeners();
  }

  /* --------------------------------------------------------------
     Public API
     -------------------------------------------------------------- */
  ask({
    title = 'Are you sure?',
    desc = '',
    buttons = null,
    cancelValue = 'cancel',
    icon = 'warning',
  } = {}) {
    if (this.#busy) {
      return Promise.reject(new Error('Dialog is already open'));
    }

    return new Promise((resolve) => {
      this.#busy = true;
      this.#resolver = resolve;
      this._resetPasswordMode();
      this._populate({ title, desc, buttons, cancelValue, icon });
      this._show();
    });
  }

  confirm({
    title = 'Are you sure?',
    message = '',
    confirmLabel = 'Confirm',
    cancelLabel = 'Cancel',
    variant = 'primary',
    icon = 'warning',
  } = {}) {
    return this.ask({
      title,
      desc: message,
      icon,
      buttons: [
        { value: 'confirm', label: confirmLabel, variant },
        { value: 'cancel',  label: cancelLabel,  variant: 'ghost' },
      ],
      cancelValue: 'cancel',
    }).then(v => v === 'confirm');
  }

  alert({
    title = 'Notice',
    message = '',
    closeLabel = 'OK',
    icon = 'info',
  } = {}) {
    return this.ask({
      title,
      desc: message,
      icon,
      buttons: [
        { value: 'ok', label: closeLabel, variant: 'primary' },
      ],
      cancelValue: 'ok',
    });
  }

  /**
   * Show a dialog with a password input. The promise resolves with
   * the password string (on confirm) or null (on cancel/escape).
   */
  passwordConfirm({
    title = 'Confirm with password',
    message = '',
    confirmLabel = 'Confirm',
    cancelLabel = 'Cancel',
    icon = 'warning',
  } = {}) {
    if (this.#busy) {
      return Promise.resolve(null);
    }

    return new Promise((resolve) => {
      this.#busy = true;
      this.#resolver = (value) => resolve(value);

      // Enable password mode
      this.#refs.body.hidden = false;
      this.#refs.body.innerHTML = `
        <input type="password"
               class="cascade-dialog-password-input"
               autocomplete="current-password"
               placeholder="Enter your password" />
      `;
      this.#passwordInput = this.#refs.body.querySelector('input');
      this.#passwordInput.addEventListener('keydown', this._onPasswordKey);

      this._populate({
        title,
        desc: message,
        icon,
        buttons: [
          { value: '__password__', label: confirmLabel, variant: 'primary' },
          { value: '__cancel__',   label: cancelLabel,  variant: 'ghost' },
        ],
        cancelValue: '__cancel__',
      });

      this._show();

      // Autofocus the input after the transition begins
      setTimeout(() => {
        this.#passwordInput && this.#passwordInput.focus();
      }, 200);
    });
  }

  close(value = 'cancel') {
    this._resolve(value);
  }

  /* --------------------------------------------------------------
     Rendering
     -------------------------------------------------------------- */
  _render() {
    this.innerHTML = `
      <div class="cascade-dialog-backdrop" role="dialog" aria-modal="true">
        <div class="cascade-dialog">
          <div class="cascade-dialog-head">
            <span class="cascade-dialog-icon" data-role="icon"></span>
            <div class="cascade-dialog-text">
              <div class="cascade-dialog-title" data-role="title"></div>
              <div class="cascade-dialog-desc" data-role="desc"></div>
            </div>
          </div>
          <div class="cascade-dialog-body" data-role="body" hidden></div>
          <div class="cascade-dialog-actions" data-role="actions"></div>
        </div>
      </div>
    `;
  }

  _cacheRefs() {
    this.#refs = {
      backdrop: this.querySelector('.cascade-dialog-backdrop'),
      icon:     this.querySelector('[data-role="icon"]'),
      title:    this.querySelector('[data-role="title"]'),
      desc:     this.querySelector('[data-role="desc"]'),
      body:     this.querySelector('[data-role="body"]'),
      actions:  this.querySelector('[data-role="actions"]'),
    };
  }

  _attachListeners() {
    this._onBackdropClick = (e) => {
      if (e.target === this.#refs.backdrop) this._resolve(this.#cancelValue);
    };
    this._onEsc = (e) => {
      if (e.key === 'Escape' && this.#busy) this._resolve(this.#cancelValue);
    };
    this.#refs.backdrop.addEventListener('click', this._onBackdropClick);
    document.addEventListener('keydown', this._onEsc);
  }

  _detachListeners() {
    if (this.#refs.backdrop && this._onBackdropClick) {
      this.#refs.backdrop.removeEventListener('click', this._onBackdropClick);
    }
    if (this._onEsc) {
      document.removeEventListener('keydown', this._onEsc);
    }
  }

  _resetPasswordMode() {
    if (this.#passwordInput) {
      this.#passwordInput.removeEventListener('keydown', this._onPasswordKey);
      this.#passwordInput = null;
    }
    if (this.#refs.body) {
      this.#refs.body.hidden = true;
      this.#refs.body.innerHTML = '';
    }
  }

  _onPasswordKey = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      this._resolve('__password__');
    }
  };

  _populate({ title, desc, buttons, cancelValue, icon }) {
    this.#cancelValue = cancelValue || 'cancel';

    this.#refs.title.textContent = title || '';
    this.#refs.desc.innerHTML = desc || '';

    const ICONS = {
      warning: '<circle cx="12" cy="12" r="9"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
      danger:  '<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
      info:    '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
      success: '<circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/>',
      lock:    '<rect x="4" y="10" width="16" height="11" rx="3"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    };
    const svgPath = ICONS[icon] || ICONS.warning;
    this.#refs.icon.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        ${svgPath}
      </svg>
    `;

    this.#refs.icon.classList.remove('is-warning', 'is-danger', 'is-info', 'is-success', 'is-lock');
    this.#refs.icon.classList.add(`is-${icon || 'warning'}`);

    this.#refs.actions.innerHTML = '';
    const list = (buttons && buttons.length)
      ? buttons
      : [{ value: 'ok', label: 'OK', variant: 'primary' }];

    list.forEach((b) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = b.label || 'OK';
      btn.className = `cascade-btn-${b.variant || 'primary'}`;
      btn.addEventListener('click', () => this._resolve(b.value));
      this.#refs.actions.appendChild(btn);
    });
  }

  _show() {
    this.#refs.backdrop.classList.add('show');
    document.body.classList.add('no-scroll');
  }

  _hide() {
    this.#refs.backdrop.classList.remove('show');
    document.body.classList.remove('no-scroll');
  }

  _resolve(value) {
    if (!this.#busy) return;

    const resolver = this.#resolver;
    this.#resolver = null;
    this.#busy = false;

    // Special password-mode values
    if (value === '__password__') {
      const pwd = this.#passwordInput ? this.#passwordInput.value : '';
      if (!pwd || !pwd.trim()) {
        // Don't close — user pressed confirm with empty input
        this.#busy = true;
        this.#resolver = resolver;
        if (this.#passwordInput) {
          this.#passwordInput.classList.add('is-invalid');
          this.#passwordInput.focus();
          setTimeout(() => this.#passwordInput && this.#passwordInput.classList.remove('is-invalid'), 800);
        }
        return;
      }
      this._hide();
      this._resetPasswordMode();
      if (resolver) resolver(pwd);
      return;
    }

    if (value === '__cancel__') {
      this._hide();
      this._resetPasswordMode();
      if (resolver) resolver(null);
      return;
    }

    // Normal mode
    this._hide();
    this._resetPasswordMode();
    if (resolver) resolver(value);
  }
}

defineComponent('ramz-dialog', RamzDialog);
