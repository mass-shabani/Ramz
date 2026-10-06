// Entry point — imports every component so they auto-register.
import './components/brand.js';
import './components/promo.js';
import './components/sidebar.js';
import './components/sidebar-menu-item.js';
import './components/sidebar-menu-group.js';
import './components/collapse-button.js';
import './components/hamburger-button.js';
import './components/search.js';
import './components/notification-panel.js';
import './components/user-menu.js';
import './components/card.js';
import './components/card-stat.js';
import './components/card-content.js';
import './components/coin-watchlist.js';
import './components/content-container.js';

/* ============================================================
   Global coordination between dropdowns
   ============================================================ */
window.addEventListener('nebula:close-dropdowns', (e) => {
  const except = e.detail?.except;
  if (except !== 'notifications') {
    document.querySelectorAll('nebula-notification-panel').forEach(el => el.close?.());
  }
  if (except !== 'user-menu') {
    document.querySelectorAll('nebula-user-menu').forEach(el => el.close?.());
  }
  if (except !== 'search') {
    document.querySelectorAll('nebula-search').forEach(el => el.close?.());
  }
});

/* ============================================================
   Global overlay click → close mobile sidebar
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('overlay');
  if (overlay) {
    overlay.addEventListener('click', () => {
      document.querySelectorAll('nebula-sidebar').forEach(s => s.close?.());
      window.dispatchEvent(new CustomEvent('nebula:close-dropdowns'));
    });
  }
});

/* ============================================================
   Keyboard shortcut: ⌘K / Ctrl+K
   ============================================================ */
document.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    const search = document.querySelector('nebula-search');
    if (!search) return;
    if (window.innerWidth <= 860) search.openMobile?.();
    else search.focusDesktop?.();
  }
});

/* ============================================================
   Global ESC handler
   ============================================================ */
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    window.dispatchEvent(new CustomEvent('nebula:close-dropdowns'));
    document.querySelectorAll('nebula-search').forEach(s => s.close?.());
    document.querySelectorAll('nebula-sidebar').forEach(s => s.close?.());
  }
});