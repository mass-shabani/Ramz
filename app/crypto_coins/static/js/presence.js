/**
 * presence.js — presence heartbeat for crypto_coins partials.
 *
 * Purpose
 * -------
 *   The crypto_market poller is conditional on
 *   presence.active_count() > 0. Without heartbeat from an active
 *   UI, no provider API is called. This script keeps the poller
 *   alive while the user is on a coins partial, and releases
 *   presence on unload so the poller can go idle.
 *
 * Scope
 * -----
 *   Loaded as a content script for BOTH:
 *     • /crypto/coins/partials/list
 *     • /crypto/coins/partials/settings
 *   Registered via crypto_coins/module.py using
 *   component_service.register_content_script(...).
 *
 * Lifecycle
 * ---------
 *   • On script load (a coins partial is now showing):
 *       startHeartbeat() — sends immediately, then every 30s.
 *
 *   • On ramz:content-loaded (content-container navigation):
 *       If the new URL is still a coins partial → ensure running.
 *       If the new URL is NOT a coins partial → stop heartbeat.
 *
 *   • On beforeunload / pagehide:
 *       sendLeaveBeacon() — POST /crypto/presence/leave with
 *       navigator.sendBeacon, so the poller can idle immediately
 *       instead of waiting for the 90s TTL.
 *
 * Idempotency
 * -----------
 *   If the script is re-executed (user navigates coins_list →
 *   coins_settings → coins_list), the guards below ensure only
 *   ONE interval timer and ONE set of window listeners exist.
 *
 * Why separate from coins_list.js / coins_settings.js?
 *   Presence is a distinct concern (keep poller warm vs. render
 *   table vs. save settings). Keeping it separate means
 *   crypto_charts or other future partials can register the same
 *   file with a different `kinds` list without touching those
 *   partial-specific initializers.
 *
 * No dependencies on any framework or Ramz JS module. Pure vanilla.
 */
(function () {
  'use strict';

  const HEARTBEAT_INTERVAL_MS = 30000;
  const COINS_URL_PATTERNS = [
    '/crypto/coins/partials/list',
    '/crypto/coins/partials/settings',
  ];

  const TIMER_KEY              = '__cryptoCoinsHeartbeatTimer';
  const CONTENT_LISTENER_KEY   = '__cryptoCoinsHeartbeatContentListener';
  const UNLOAD_LISTENER_KEY    = '__cryptoCoinsHeartbeatUnloadListener';

  /* ------------------------------------------------------------ */
  /* URL matching                                                 */
  /* ------------------------------------------------------------ */
  function isCoinsUrl(url) {
    if (!url) return false;
    let pathname = url;
    try {
      pathname = new URL(url, window.location.origin).pathname;
    } catch (_) {
      // Fallback: url may already be a pathname
    }
    for (const p of COINS_URL_PATTERNS) {
      if (pathname === p) return true;
      if (pathname.indexOf(p + '/') === 0) return true;
      if (pathname.indexOf(p + '?') === 0) return true;
    }
    return false;
  }

  /* ------------------------------------------------------------ */
  /* Heartbeat                                                    */
  /* ------------------------------------------------------------ */
  function sendHeartbeat() {
    fetch('/crypto/presence/heartbeat', {
      method: 'POST',
      headers: {
        'Content-Type':     'application/json',
        'Accept':           'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
      body: JSON.stringify({ kinds: ['coins'] }),
    }).catch(function () {
      // Silent — a missing heartbeat will be retried on the next
      // interval; the poller also has a 90s TTL tolerance.
    });
  }

  function startHeartbeat() {
    if (window[TIMER_KEY]) return;   // already running
    sendHeartbeat();                 // immediate first beat
    window[TIMER_KEY] = setInterval(
      sendHeartbeat, HEARTBEAT_INTERVAL_MS
    );
  }

  function stopHeartbeat() {
    if (window[TIMER_KEY]) {
      clearInterval(window[TIMER_KEY]);
      window[TIMER_KEY] = null;
    }
  }

  /* ------------------------------------------------------------ */
  /* Leave beacon (on unload)                                     */
  /* ------------------------------------------------------------ */
  function sendLeaveBeacon() {
    try {
      const payload = JSON.stringify({ kinds: ['coins'] });
      if (navigator.sendBeacon) {
        // sendBeacon with Blob lets us control Content-Type;
        // required so the backend's _parse_body treats it as
        // application/json rather than text/plain.
        const blob = new Blob([payload], {
          type: 'application/json',
        });
        navigator.sendBeacon('/crypto/presence/leave', blob);
      } else {
        // Fallback: keepalive fetch (supported in all modern
        // browsers; may be dropped in very old ones, but the 90s
        // TTL catches that case).
        fetch('/crypto/presence/leave', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'same-origin',
          body: payload,
          keepalive: true,
        }).catch(function () { /* silent */ });
      }
    } catch (_) {
      // Nothing to do — best-effort.
    }
  }

  /* ------------------------------------------------------------ */
  /* Navigation listener (idempotent)                             */
  /* ------------------------------------------------------------ */
  if (!window[CONTENT_LISTENER_KEY]) {
    window[CONTENT_LISTENER_KEY] = function (e) {
      const url = (e && e.detail && e.detail.url) || '';
      if (isCoinsUrl(url)) {
        startHeartbeat();
      } else {
        stopHeartbeat();
      }
    };
    window.addEventListener(
      'ramz:content-loaded',
      window[CONTENT_LISTENER_KEY]
    );
  }

  /* ------------------------------------------------------------ */
  /* Unload listener (idempotent)                                 */
  /* ------------------------------------------------------------ */
  if (!window[UNLOAD_LISTENER_KEY]) {
    window[UNLOAD_LISTENER_KEY] = function () {
      sendLeaveBeacon();
    };
    window.addEventListener(
      'beforeunload', window[UNLOAD_LISTENER_KEY]
    );
    window.addEventListener(
      'pagehide', window[UNLOAD_LISTENER_KEY]
    );
  }

  /* ------------------------------------------------------------ */
  /* Start immediately                                            */
  /* ------------------------------------------------------------ */
  // This script is only loaded when a coins partial is showing,
  // so we are certain the user is on a coins URL right now.
  startHeartbeat();
})();
