import { defineComponent } from '../_base.js';

/**
 * <ramz-hamburger-btn>
 *
 * Opens the sidebar's mobile drawer. Locates the closest <ramz-sidebar>
 * in the document and calls its public open() method.
 *
 * Only displayed on small screens (handled by CSS via the .hamburger-btn
 * selector and the media query in style.css).
 */
class RamzHamburgerBtn extends HTMLElement {
  connectedCallback() {
    this._render();
    this.addEventListener('click', this._onClick);
  }

  disconnectedCallback() {
    this.removeEventListener('click', this._onClick);
  }

  _onClick = (e) => {
    const btn = e.target.closest('.hamburger-btn');
    if (!btn || !this.contains(btn)) return;

    const sidebar = document.querySelector('ramz-sidebar');
    if (sidebar && typeof sidebar.open === 'function') {
      sidebar.open();
    }
  };

  _render() {
    this.innerHTML = `
      <button class="hamburger-btn" type="button" aria-label="Open menu">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 7h16"/>
          <path d="M4 12h10"/>
          <path d="M4 17h16"/>
        </svg>
      </button>
    `;
  }
}

defineComponent('ramz-hamburger-btn', RamzHamburgerBtn);