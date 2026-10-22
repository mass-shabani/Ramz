import { defineComponent, attr, emit, escapeHtml } from '../_base.js';

const DEFAULT_EMPTY_TEXT = 'No records found.';

/**
 * <ramz-table>
 *
 * A reusable data table component (Light DOM).
 *
 * Attributes:
 *   • title         — card header title
 *   • subtitle      — card header subtitle
 *   • endpoint      — optional URL to POST for live data (JSON: {columns, rows})
 *   • empty-text    — text shown when there are no rows (default: "No records found.")
 *   • hide-header   — if present, the card header is not rendered
 *
 * Slot:
 *   • header-actions — content rendered on the right side of the header
 *
 * Public API:
 *   • setColumns(columns) — configure columns (see schema below)
 *   • setData(rows)       — replace data
 *   • setLoading(loading) — toggle loading state
 *   • reload()            — re-fetch data from endpoint (if set)
 *   • getRowData(index)   — read the raw row object
 *
 * Column schema:
 *   {
 *     key:       "name",         // required — property name on each row
 *     label:     "Name",         // required — header text
 *     type:      "text",         // optional — one of:
 *                                //   "text" | "html" | "avatar" | "badge"
 *                                //   "date" | "number" | "actions"
 *     align:     "left",         // optional — "left" | "center" | "right"
 *     width:     "200px",        // optional — CSS width
 *     className: "custom"        // optional — extra class on <td>
 *   }
 *
 * Cell value shapes:
 *   type "text"    — string (HTML-escaped before render)
 *   type "html"    — string (rendered raw; caller is responsible for safety)
 *   type "avatar"  — { initials, name?, email?, avatarClass? }
 *   type "badge"   — { text, variant }   variant ∈ "active" | "pending" | "idle"
 *   type "date"    — ISO date string
 *   type "number"  — number
 *   type "actions" — array of action objects:
 *                    { label, icon?, href?, action?, variant?, data? }
 *                    icon: HTML string (raw) or plain text (escaped)
 *                    variant: CSS class (e.g. "danger")
 *                    data: extra data-* attributes
 *
 * Emits:
 *   • ramz:table-row-click — { row, rowIndex }
 *   • ramz:table-action    — { action, row, rowIndex, data }
 *   • ramz:table-loaded    — { url, rowCount }
 *   • ramz:table-error     — { url, status, error }
 */
class RamzTable extends HTMLElement {
  static get observedAttributes() {
    return ['title', 'subtitle', 'endpoint', 'empty-text', 'hide-header'];
  }

  #columns = [];
  #rows = [];
  #loading = false;
  #error = null;
  #refs = {};
  #capturedHeaderActions = null;
  #built = false;
  #fetching = false;

  /* --------------------------------------------------------------
     Lifecycle
     -------------------------------------------------------------- */
  connectedCallback() {
    if (!this.#built) {
      this.#captureHeaderActions();
      this.#built = true;
    }
    this._render();
    this._attachListeners();
    this._renderBody();

    const endpoint = attr(this, 'endpoint', '');
    if (endpoint && this.#rows.length === 0) {
      this.reload();
    }
  }

  disconnectedCallback() {
    this._detachListeners();
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal) return;
    if (!this.isConnected || !this.#built) return;
    this._render();
    this._attachListeners();
    this._renderBody();
  }

  /* --------------------------------------------------------------
     Public API
     -------------------------------------------------------------- */
  setColumns(columns) {
    if (!Array.isArray(columns)) return;
    this.#columns = columns.slice();
    if (this.isConnected) this._renderBody();
  }

  setData(rows) {
    if (!Array.isArray(rows)) return;
    this.#rows = rows.slice();
    this.#error = null;
    if (this.isConnected) this._renderBody();
  }

  setLoading(loading) {
    this.#loading = Boolean(loading);
    if (this.isConnected) this._renderBody();
  }

  getRowData(index) {
    return this.#rows[index] || null;
  }

  async reload() {
    const endpoint = attr(this, 'endpoint', '');
    if (!endpoint || this.#fetching) return;

    this.#fetching = true;
    this.#loading = true;
    this.#error = null;
    this._renderBody();

    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json',
        },
        credentials: 'same-origin',
      });

      if (!resp.ok) {
        throw Object.assign(
          new Error('HTTP ' + resp.status),
          { status: resp.status }
        );
      }

      const data = await resp.json();

      if (Array.isArray(data.columns)) this.#columns = data.columns;
      if (Array.isArray(data.rows))    this.#rows = data.rows;

      this.#loading = false;
      this._renderBody();
      emit(this, 'ramz:table-loaded', {
        url: endpoint,
        rowCount: this.#rows.length,
      });

    } catch (err) {
      console.error('[ramz-table] reload failed:', err);
      this.#loading = false;
      this.#error = err;
      this._renderBody();
      emit(this, 'ramz:table-error', {
        url: endpoint,
        status: err.status,
        error: err.message,
      });

    } finally {
      this.#fetching = false;
    }
  }

  /* --------------------------------------------------------------
     Capture header actions slot
     -------------------------------------------------------------- */
  #captureHeaderActions() {
    this.#capturedHeaderActions = Array.from(this.children)
      .filter(el => el.getAttribute('slot') === 'header-actions');
  }

  /* --------------------------------------------------------------
     Shell
     -------------------------------------------------------------- */
  _render() {
    const title      = attr(this, 'title', '');
    const subtitle   = attr(this, 'subtitle', '');
    const hideHeader = this.hasAttribute('hide-header');

    const hasHeaderActions =
      this.#capturedHeaderActions && this.#capturedHeaderActions.length > 0;
    const hasHeader = !hideHeader && (title || subtitle || hasHeaderActions);

    this.innerHTML = '';

    const card = document.createElement('div');
    card.className = 'card';

    if (hasHeader) {
      const head = document.createElement('div');
      head.className = 'card-head';

      const headLeft = document.createElement('div');
      headLeft.className = 'card-head-left';

      if (title || subtitle) {
        const headText = document.createElement('div');
        headText.className = 'card-head-text';

        if (title) {
          const t = document.createElement('div');
          t.className = 'card-title';
          t.textContent = title;
          headText.appendChild(t);
        }
        if (subtitle) {
          const s = document.createElement('div');
          s.className = 'card-sub';
          s.textContent = subtitle;
          headText.appendChild(s);
        }
        headLeft.appendChild(headText);
      }
      head.appendChild(headLeft);

      if (hasHeaderActions) {
        const actionsWrap = document.createElement('div');
        actionsWrap.className = 'card-head-actions';
        this.#capturedHeaderActions.forEach(el => actionsWrap.appendChild(el));
        head.appendChild(actionsWrap);
      }

      card.appendChild(head);
    }

    const wrap = document.createElement('div');
    wrap.className = 'table-wrap';

    const table = document.createElement('table');
    const thead = document.createElement('thead');
    const headTr = document.createElement('tr');
    thead.appendChild(headTr);
    const tbody = document.createElement('tbody');
    table.appendChild(thead);
    table.appendChild(tbody);
    wrap.appendChild(table);
    card.appendChild(wrap);

    this.appendChild(card);

    this.#refs = {
      card,
      thead: headTr,
      tbody,
    };
  }

  /* --------------------------------------------------------------
     Body
     -------------------------------------------------------------- */
  _renderBody() {
    if (!this.#refs.thead || !this.#refs.tbody) return;

    this.#refs.thead.innerHTML = this.#columns.map(col => {
      const parts = [];
      if (col.align) parts.push(`text-align:${col.align};`);
      if (col.width) parts.push(`width:${col.width};`);
      const style = parts.length ? ` style="${parts.join('')}"` : '';
      return `<th${style}>${escapeHtml(col.label || '')}</th>`;
    }).join('');

    this.#refs.card.classList.toggle('is-loading', this.#loading);

    if (this.#error) {
      const colCount = this.#columns.length || 1;
      this.#refs.tbody.innerHTML = `
        <tr>
          <td colspan="${colCount}"
              style="text-align:center;padding:32px;color:var(--danger);">
            Failed to load data.
            <button type="button" data-action="__retry__"
                    style="color:var(--primary-light);background:none;border:none;
                           cursor:pointer;font-weight:600;margin-left:6px;">
              Retry
            </button>
          </td>
        </tr>`;
      return;
    }

    if (this.#rows.length === 0) {
      const colCount = this.#columns.length || 1;
      const emptyText = attr(this, 'empty-text', DEFAULT_EMPTY_TEXT);
      this.#refs.tbody.innerHTML = `
        <tr>
          <td colspan="${colCount}"
              style="text-align:center;padding:32px;color:var(--muted);">
            ${escapeHtml(emptyText)}
          </td>
        </tr>`;
      return;
    }

    this.#refs.tbody.innerHTML = this.#rows
      .map((row, idx) => this._renderRow(row, idx))
      .join('');
  }

  _renderRow(row, rowIndex) {
    const cells = this.#columns
      .map(col => this._renderCell(row, col, rowIndex))
      .join('');
    return `<tr data-row-index="${rowIndex}">${cells}</tr>`;
  }

  _renderCell(row, col, rowIndex) {
    const rawValue = row[col.key];
    const type = col.type || 'text';

    const parts = [];
    if (col.align) parts.push(`text-align:${col.align};`);
    const styleAttr = parts.length ? ` style="${parts.join('')}"` : '';

    const classNameParts = [];
    if (col.className) classNameParts.push(col.className);
    const classAttr = classNameParts.length
      ? ` class="${classNameParts.join(' ')}"`
      : '';

    let inner = '';

    switch (type) {
      case 'html':
        inner = rawValue == null ? '' : String(rawValue);
        break;

      case 'avatar': {
        const v = rawValue || {};
        const initials   = escapeHtml(v.initials || '?');
        const avatarCls  = escapeHtml(v.avatarClass || '');
        const nameText   = escapeHtml(v.name || '');
        const emailText  = v.email ? escapeHtml(v.email) : '';
        inner = `
          <div class="cell-user">
            <span class="avatar ${avatarCls}">${initials}</span>
            <div>
              <div class="cu-name">${nameText}</div>
              ${emailText ? `<div class="cu-mail">${emailText}</div>` : ''}
            </div>
          </div>`;
        break;
      }

      case 'badge': {
        const v = rawValue || {};
        const variant = escapeHtml(v.variant || 'idle');
        const text    = escapeHtml(v.text || '');
        inner = `<span class="status ${variant}">${text}</span>`;
        break;
      }

      case 'date': {
        if (!rawValue) {
          inner = '—';
          break;
        }
        const d = new Date(rawValue);
        if (isNaN(d.getTime())) {
          inner = '—';
        } else {
          inner = `<span class="date">${escapeHtml(d.toLocaleDateString())}</span>`;
        }
        break;
      }

      case 'number': {
        const n = Number(rawValue);
        if (!Number.isFinite(n)) {
          inner = '—';
        } else {
          inner = `<span class="amount">${n.toLocaleString()}</span>`;
        }
        break;
      }

      case 'actions': {
        const actions = Array.isArray(rawValue) ? rawValue : [];
        inner = `<div class="channel-actions">${actions
          .map(a => this._renderActionBtn(a, rowIndex))
          .join('')}</div>`;
        break;
      }

      case 'text':
      default:
        inner = escapeHtml(String(rawValue == null ? '' : rawValue));
        break;
    }

    return `<td${classAttr}${styleAttr}>${inner}</td>`;
  }

  _renderActionBtn(action, rowIndex) {
    const label = action.label ? escapeHtml(action.label) : '';

    let icon = '';
    if (action.icon) {
      const raw = String(action.icon).trim();
      icon = raw.startsWith('<') ? raw : escapeHtml(raw);
    }

    const variant = action.variant ? ` ${escapeHtml(action.variant)}` : '';
    const actionName = action.action
      ? ` data-action="${escapeHtml(action.action)}"`
      : '';

    let extraData = '';
    if (action.data && typeof action.data === 'object') {
      extraData = Object.entries(action.data)
        .map(([k, v]) => ` data-${escapeHtml(k)}="${escapeHtml(String(v))}"`)
        .join('');
    }

    const common = `${actionName} data-row-index="${rowIndex}"${extraData}`;

    if (action.href) {
      return `<a class="channel-action${variant}"
                 href="${escapeHtml(action.href)}"${common}>${icon}${label}</a>`;
    }
    return `<button type="button"
                    class="channel-action${variant}"${common}>${icon}${label}</button>`;
  }

  /* --------------------------------------------------------------
     Listeners
     -------------------------------------------------------------- */
  _attachListeners() {
    this.addEventListener('click', this._onClick);
  }

  _detachListeners() {
    this.removeEventListener('click', this._onClick);
  }

  _onClick = (e) => {
    const retry = e.target.closest('[data-action="__retry__"]');
    if (retry && this.contains(retry)) {
      this.reload();
      return;
    }

    const actionBtn = e.target.closest('[data-action]');
    if (actionBtn && this.contains(actionBtn)) {
      const actionName = actionBtn.dataset.action;
      if (actionName === '__retry__') return;

      const rowIndex = parseInt(actionBtn.dataset.rowIndex, 10);
      if (!Number.isFinite(rowIndex)) return;

      const row = this.#rows[rowIndex];
      if (!row) return;

      emit(this, 'ramz:table-action', {
        action: actionName,
        row,
        rowIndex,
        data: { ...actionBtn.dataset },
      });
      return;
    }

    const tr = e.target.closest('tr[data-row-index]');
    if (tr && this.contains(tr)) {
      const rowIndex = parseInt(tr.dataset.rowIndex, 10);
      if (!Number.isFinite(rowIndex)) return;

      const row = this.#rows[rowIndex];
      if (!row) return;

      emit(this, 'ramz:table-row-click', { row, rowIndex });
    }
  };
}

defineComponent('ramz-table', RamzTable);
