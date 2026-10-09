import { defineComponent, attr, emit } from '../_base.js';

/**
 * <ramz-promo>
 *
 * Attributes:
 *   • title         — promo headline
 *   • text          — supporting copy
 *   • button-label  — CTA button text
 *
 * Emits:
 *   • promo-click   — when the CTA button is clicked
 */
class RamzPromo extends HTMLElement {
  static get observedAttributes() {
    return ['title', 'text', 'button-label'];
  }

  connectedCallback() {
    this._render();
    this.addEventListener('click', this._onClick);
  }

  disconnectedCallback() {
    this.removeEventListener('click', this._onClick);
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal !== newVal && this.isConnected) {
      this._render();
    }
  }

  _onClick = (e) => {
    const btn = e.target.closest('.promo button');
    if (btn && this.contains(btn)) {
      emit(this, 'promo-click');
    }
  };

  _render() {
    const title       = attr(this, 'title', 'Upgrade to Pro');
    const text        = attr(this, 'text',
      'Unlock advanced AI predictions, unlimited alerts and priority support.');
    const buttonLabel = attr(this, 'button-label', 'Upgrade Now');

    this.innerHTML = `
      <div class="promo">
        <h4>${title}</h4>
        <p>${text}</p>
        <button type="button">${buttonLabel}</button>
      </div>
    `;
  }
}

defineComponent('ramz-promo', RamzPromo);