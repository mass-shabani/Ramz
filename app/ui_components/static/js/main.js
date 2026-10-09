/* ==========================================================================
   Ramz Web Components — entry point
   --------------------------------------------------------------------------
   Importing a component file is enough to register it. The rest of this
   file only wires up cross-component coordination.
   ========================================================================== */

/* ---------- Phase 1 — static display components ---------- */
import './components/brand.js';
import './components/promo.js';
import './components/menu-group.js';
import './components/progress-bar.js';
import './components/collapse-button.js';
import './components/hamburger-button.js'
import './components/notification-panel.js';
import './components/user-menu.js';
import './components/search.js';
import './components/sidebar.js';
import './components/menu-item.js';
import './components/content-container.js';
import './components/progress-bar.js';
import './components/card.js';


/* ==========================================================================
   Global coordination
   ========================================================================== */

/**
 * Close every open dropdown, except the one that requested it.
 * Fired by any component that opens a dropdown so the others collapse.
 */
window.addEventListener('ramz:close-dropdowns', (e) => {
  const except = e.detail?.except;

  if (except !== 'notifications') {
    document.querySelectorAll('ramz-notifications')
      .forEach(el => el.close?.());
  }
  if (except !== 'user-menu') {
    document.querySelectorAll('ramz-user-menu')
      .forEach(el => el.close?.());
  }
  if (except !== 'search') {
    document.querySelectorAll('ramz-search')
      .forEach(el => el.close?.());
  }
});

/**
 * Mobile overlay click → close sidebar and any open dropdown.
 */
document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('overlay');
  if (!overlay) return;

  overlay.addEventListener('click', () => {
    document.querySelectorAll('ramz-sidebar')
      .forEach(s => s.close?.());
    window.dispatchEvent(new CustomEvent('ramz:close-dropdowns'));
  });
});

/**
 * ⌘K / Ctrl+K → open search.
 * On mobile, opens the modal; on desktop, focuses the inline input.
 */
document.addEventListener('keydown', (e) => {
  if (!(e.metaKey || e.ctrlKey)) return;
  if (e.key.toLowerCase() !== 'k') return;

  e.preventDefault();
  const search = document.querySelector('ramz-search');
  if (!search) return;

  if (window.innerWidth <= 860) search.openMobile?.();
  else search.focusDesktop?.();
});

/**
 * ESC → close every transient UI element.
 */
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;

  window.dispatchEvent(new CustomEvent('ramz:close-dropdowns'));
  document.querySelectorAll('ramz-search')
    .forEach(s => s.close?.());
  document.querySelectorAll('ramz-sidebar')
    .forEach(s => s.close?.());
});