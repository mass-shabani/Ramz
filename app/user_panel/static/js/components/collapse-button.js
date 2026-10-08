import { defineComponent, attr, emit } from '../_base.js';

/**
 * <ramz-collapse-btn>
 *
 * A button that asks the parent sidebar to toggle its collapsed /
 * expanded state. It does not hold any state itself — the sidebar
 * owns the state and reflects it back on the button.
 *
 * Attributes:
 *   • label        — default button text (default: "Collapse Menu")
 *   • label-collapsed — text to show when the sidebar is collapsed
 *
 * Emits:
 *   • ramz:sidebar-toggle — bubbles to the parent <ramz-sidebar>
 */
class RamzCollapseBtn extends HTMLElement {
  static get observedAttributes() {
    return ['label', 'label-collapsed', 'collapsed'];
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
    const btn = e.target.closest('.collapse-btn');
    if (btn && this.contains(btn)) {
      emit(this, 'ramz:sidebar-toggle');
    }
  };

  _render() {
    const collapsed = this.hasAttribute('collapsed');
    const label = collapsed
      ? attr(this, 'label-collapsed', 'Expand Menu')
      : attr(this, 'label',           'Collapse Menu');

    this.innerHTML = `
      <div class="sidebar-footer">
        <button class="collapse-btn" type="button" aria-label="${label}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 17l-5-5 5-5"/>
            <path d="M18 17l-5-5 5-5"/>
          </svg>
          <span class="collapse-text">${label}</span>
        </button>
      </div>
    `;
  }
}

defineComponent('ramz-collapse-btn', RamzCollapseBtn);