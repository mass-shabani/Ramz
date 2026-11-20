/**
 * coins_list.js — behavior for the coin list partial (TASK 79.5).
 *
 * Scope
 * -----
 *   • Favorite toggle: click the star in the table → POST to
 *     /crypto/coins/api/favorite/toggle.
 *
 * Why a separate file (not inline <script>)?
 *   content-container injects the partial via `element.innerHTML = html`.
 *   Inline scripts inserted via innerHTML do not execute per HTML5 spec.
 *   content-container re-injects each <script> as a fresh element after
 *   setting innerHTML, which triggers normal fetch + execution
 *   (fetch + (0, eval) for classic scripts). Keeping behavior in an
 *   external .js file is the supported mechanism (see coins_settings.js
 *   for the same pattern).
 *
 * Anti-duplication
 * ----------------
 * If the user navigates away and back, coins_list.html is re-injected
 * and this script re-executes. The handler is idempotent: a previous
 * listener (tracked on window) is removed before a new one is attached.
 *
 * Error handling
 * --------------
 *   • No user-visible banner on network/server errors — silent fail
 *     keeps the table usable. console.error only for debugging.
 *   • Optimistic UI: NOT used. Button state changes only after the
 *     server confirms success (avoids the UI and DB drifting apart).
 *
 * No dependencies on any framework or Ramz JS module. Pure vanilla.
 */
(function () {
  'use strict';

  const ENDPOINT     = '/crypto/coins/api/favorite/toggle';
  const HANDLER_KEY  = '__cryptoCoinsFavoriteHandler';

  // Anti-duplication: remove previous listener (from a prior injection).
  if (window[HANDLER_KEY]) {
    document.removeEventListener('click', window[HANDLER_KEY]);
  }

  window[HANDLER_KEY] = async function (e) {
    const btn = e.target && e.target.closest
      ? e.target.closest('.favorite-btn')
      : null;
    if (!btn) return;

    // Defensive: if the button was detached between click and handler
    // execution (e.g., table reloaded mid-flight), do nothing.
    if (!document.body.contains(btn)) return;

    const canonical = btn.getAttribute('data-canonical');
    if (!canonical) return;

    // Guard: ignore clicks while a previous request is in-flight.
    if (btn.disabled) return;
    btn.disabled = true;

    const currentlyFavorited = btn.getAttribute('data-favorited') === '1';
    const action = currentlyFavorited ? 'remove' : 'add';

    try {
      const r = await fetch(ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type':     'application/json',
          'Accept':           'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          canonical: canonical,
          action:    action,
        }),
      });

      const data = await r.json();

      if (data && data.status === 'success') {
        const isNowFavorited = !!data.favorited;
        btn.setAttribute('data-favorited', isNowFavorited ? '1' : '0');
        btn.textContent = isNowFavorited ? '★' : '☆';
        btn.classList.toggle('favorite-btn--active', isNowFavorited);
        btn.style.color = isNowFavorited ? '#fbbf24' : '#64748b';
        const title = isNowFavorited
          ? 'Remove from favorites'
          : 'Add to favorites';
        btn.title = title;
        btn.setAttribute('aria-label', title);
      } else {
        if (window.console && console.warn) {
          console.warn('[coins_list] favorite toggle rejected:', data);
        }
      }
    } catch (err) {
      if (window.console && console.error) {
        console.error('[coins_list] favorite toggle failed:', err);
      }
    } finally {
      btn.disabled = false;
    }
  };

  document.addEventListener('click', window[HANDLER_KEY]);
})();
