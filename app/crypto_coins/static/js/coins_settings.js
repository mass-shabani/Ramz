/**
 * coins_settings.js — behavior for the coin settings partial.
 *
 * Why a separate file (not inline <script>)?
 *   content-container injects the partial via `element.innerHTML = html`.
 *   Per HTML5 spec, <script> elements inserted via innerHTML — inline
 *   OR external — are marked "already started" and do NOT execute (the
 *   browser does not even fetch external src). content-container works
 *   around this by re-injecting each <script> as a fresh element after
 *   setting innerHTML, which triggers normal fetch + execution.
 *
 *   Keeping the behavior in a separate .js file (rather than inline)
 *   makes it independently cacheable and easier to lint/test.
 *
 * Idempotency
 * -----------
 * This file runs once per injection. If the user navigates away and
 * back, content-container replaces innerHTML, the script runs again,
 * and it attaches handlers to the NEW elements (old ones are detached
 * and harmless). If the required elements are missing (e.g., the
 * script runs before the DOM is fully built — shouldn't happen, but
 * defensively handled), we exit early.
 *
 * No dependencies on any framework or Ramz JS modules. Pure vanilla.
 */
(function () {
  'use strict';

  const form     = document.getElementById('coinsSettingsForm');
  const currency = document.getElementById('coinsDisplayCurrency');
  const rows     = document.getElementById('coinsRowsPerPage');
  const saveBtn  = document.getElementById('coinsSettingsSaveBtn');
  const statusEl = document.getElementById('coinsSettingsStatus');

  if (!form || !currency || !rows || !saveBtn || !statusEl) return;

  function showStatus(kind, message) {
    const isOk = kind === 'success';
    statusEl.style.display    = 'block';
    statusEl.style.background = isOk
      ? 'rgba(16,185,129,0.10)'
      : 'rgba(244,63,94,0.10)';
    statusEl.style.border     = isOk
      ? '1px solid rgba(16,185,129,0.28)'
      : '1px solid rgba(244,63,94,0.28)';
    statusEl.style.color      = isOk ? '#a7f3d0' : '#fecdd3';
    statusEl.textContent      = message;
  }

  function hideStatus() {
    statusEl.style.display = 'none';
    statusEl.textContent   = '';
  }

  async function load() {
    hideStatus();
    try {
      const r = await fetch('/crypto/coins/api/settings', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
      });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const d = await r.json();
      if (d.status !== 'success') return;
      currency.value = d.display_currency || 'USDT';
      rows.value     = String(d.rows_per_page || 50);
    } catch (e) {
      showStatus('error', 'Failed to load settings.');
    }
  }

  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true;
    hideStatus();
    try {
      const r = await fetch('/crypto/coins/api/settings/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          display_currency: currency.value,
          rows_per_page:    parseInt(rows.value, 10) || 50,
        }),
      });
      const d = await r.json();
      if (d.status === 'success') {
        showStatus('success',
          'Settings saved. Change will apply to the next coins list load.');
      } else {
        showStatus('error',
          d.message || 'Failed to save settings.');
      }
    } catch (e) {
      showStatus('error', 'Network error. Please try again.');
    } finally {
      saveBtn.disabled = false;
    }
  });

  load();
})();
