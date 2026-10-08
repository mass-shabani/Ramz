// app/user_panel/static/js/components/card.js

/**
 * <ramz-card> — unified card component (Light DOM)
 *
 * Attributes:
 *   • title       — card header title
 *   • subtitle    — card header subtitle
 *   • card-class  — extra CSS class(es) to add to the inner .card element
 *                   (the `class` attribute on <ramz-card> itself stays on
 *                   the host element, which uses display: contents)
 *
 * Slot-like conventions (any DOM element is accepted):
 *   • slot="icon"            — any element (img / svg / div / button / object)
 *   • slot="header-actions"  — content opposite the header
 *   • (no slot)              — card body content
 *   • slot="footer"          — footer content (replaces .trend)
 *
 * Empty sections are not rendered at all, so they consume zero space.
 * The component works in Light DOM to preserve the shared global stylesheet.
 */
export class RamzCard extends HTMLElement {
  static get observedAttributes() {
    return ['title', 'subtitle', 'card-class'];
  }

  constructor() {
    super();
    this._built     = false;
    this._scheduled = false;
    this._captured  = null;
    this._cardEl    = null;
  }

  /* --------------------------------------------------------------
     Property accessors so that `el.title = 'X'` also works
     -------------------------------------------------------------- */
  get title()     { return this.getAttribute('title')    || ''; }
  set title(v)    { this.setAttribute('title', v || ''); }

  get subtitle()  { return this.getAttribute('subtitle') || ''; }
  set subtitle(v) { this.setAttribute('subtitle', v || ''); }

  get cardClass() { return this.getAttribute('card-class') || ''; }
  set cardClass(v) {
    if (v) this.setAttribute('card-class', v);
    else   this.removeAttribute('card-class');
  }

  /* --------------------------------------------------------------
     Lifecycle
     -------------------------------------------------------------- */
  connectedCallback() {
    if (this._built || this._scheduled) return;
    this._scheduled = true;

    // Defer one microtask so that children appended immediately after
    // appendChild() are still captured correctly.
    queueMicrotask(() => {
      this._scheduled = false;
      if (!this._built) {
        this._built = true;
        this._build();
      }
    });
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal) return;
    if (!this._built) return;

    // `card-class` only touches the inner element — no rebuild needed.
    if (name === 'card-class') {
      this._applyCardClass();
      return;
    }

    // Structural attributes require a full rebuild.
    this._build();
  }

  /* --------------------------------------------------------------
     Core: build the card structure
     -------------------------------------------------------------- */
  _build() {
    /* 1. First-time capture of the user-provided children */
    if (!this._captured) {
      const children = Array.from(this.children);

      this._captured = {
        icon:    children.filter(el => el.getAttribute('slot') === 'icon'),
        actions: children.filter(el => el.getAttribute('slot') === 'header-actions'),
        footer:  children.filter(el => el.getAttribute('slot') === 'footer'),
        body:    children.filter(el => {
          const s = el.getAttribute('slot');
          return s === null || s === '';
        })
      };
    }

    /* 2. Clear everything */
    this.innerHTML = '';

    const { icon, actions, footer, body } = this._captured;
    const title    = this.getAttribute('title')    || '';
    const subtitle = this.getAttribute('subtitle') || '';

    /* 3. Root card element */
    const card = document.createElement('div');
    card.className = 'card';
    this._cardEl = card;

    /* 4. Apply extra classes (from the `card-class` attribute) */
    this._applyCardClass();

    /* ---- Header ---- */
    const hasIcon   = icon.length > 0;
    const hasHeader = !!(title || subtitle || hasIcon);

    if (hasHeader) {
      const head = document.createElement('div');
      head.className = 'card-head';

      // Left side: icon + text
      const headLeft = document.createElement('div');
      headLeft.className = 'card-head-left' + (hasIcon ? ' has-icon' : '');

      icon.forEach(el => headLeft.appendChild(el));

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

      // Right side: actions
      if (actions.length > 0) {
        const actionsWrap = document.createElement('div');
        actionsWrap.className = 'card-head-actions';
        actions.forEach(el => actionsWrap.appendChild(el));
        head.appendChild(actionsWrap);
      }

      card.appendChild(head);
    }

    /* ---- Body ---- */
    const bodyWrap = document.createElement('div');
    bodyWrap.className = 'card-body';
    body.forEach(el => bodyWrap.appendChild(el));
    card.appendChild(bodyWrap);

    /* ---- Footer ---- */
    if (footer.length > 0) {
      const footerWrap = document.createElement('div');
      footerWrap.className = 'card-footer';
      footer.forEach(el => footerWrap.appendChild(el));
      card.appendChild(footerWrap);
    }

    /* 5. Attach */
    this.appendChild(card);
  }

  /* --------------------------------------------------------------
     Apply the card-class attribute to the inner .card element
     -------------------------------------------------------------- */
  _applyCardClass() {
    if (!this._cardEl) return;

    // Strip any previously applied extra classes, keeping the base "card".
    this._cardEl.className = 'card';

    const extra = (this.getAttribute('card-class') || '').trim();
    if (extra) {
      this._cardEl.classList.add(...extra.split(/\s+/).filter(Boolean));
    }
  }
}

customElements.define('ramz-card', RamzCard);