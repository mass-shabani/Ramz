import { defineComponent, attr } from '../_base.js';

/**
 * <ramz-menu-group>
 *
 * Attributes:
 *   • label — section label rendered as `.nav-section`
 *
 * Children are preserved as-is. This component only inserts (or updates)
 * a `.nav-section` at the top of its content. If `label` is empty, no
 * section is shown.
 *
 * The component never detaches existing children, so any nested custom
 * elements keep their state and do not go through a detach / reattach cycle.
 */
class RamzMenuGroup extends HTMLElement {
  static get observedAttributes() {
    return ['label'];
  }

  connectedCallback() {
    this._ensureSection();
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal) return;
    if (this.isConnected) this._ensureSection();
  }

  _ensureSection() {
    const label   = attr(this, 'label', '');
    const first   = this.firstElementChild;
    const hasSect = first && first.classList.contains('nav-section');

    /* No label → remove section if it exists */
    if (!label) {
      if (hasSect) first.remove();
      return;
    }

    /* Existing section → just update its text */
    if (hasSect) {
      first.textContent = label;
      return;
    }

    /* Otherwise, insert a new one at the very top */
    const section = document.createElement('div');
    section.className = 'nav-section';
    section.textContent = label;
    this.prepend(section);
  }
}

defineComponent('ramz-menu-group', RamzMenuGroup);