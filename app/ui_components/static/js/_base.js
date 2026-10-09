/**
 * Ramz Web Components — shared helpers
 *
 * Small utility module imported by every component. Kept dependency-free
 * so it adds essentially nothing to the bundle size.
 */

/**
 * Register a custom element safely. Calling it twice with the same
 * name is a no-op, which prevents "already defined" errors during HMR
 * or repeated script loads.
 */
export function defineComponent(name, ctor) {
  if (!customElements.get(name)) {
    customElements.define(name, ctor);
  }
}

/** Read an attribute as a string with a fallback. */
export function attr(el, name, fallback = '') {
  const v = el.getAttribute(name);
  return v === null ? fallback : v;
}

/** Read an attribute as a boolean. */
export function boolAttr(el, name) {
  return el.hasAttribute(name);
}

/** Read an attribute as a number with a fallback. */
export function numAttr(el, name, fallback = 0) {
  const v = parseFloat(el.getAttribute(name));
  return Number.isFinite(v) ? v : fallback;
}

/**
 * Dispatch a CustomEvent that bubbles up and crosses component boundaries.
 * Used for cross-component coordination (e.g. closing dropdowns).
 */
export function emit(el, name, detail = null) {
  return el.dispatchEvent(new CustomEvent(name, {
    bubbles: true,
    composed: true,
    detail
  }));
}

/**
 * Delegated event listener. Returns a cleanup function that removes the
 * listener. Useful when a component re-renders its innerHTML frequently.
 *
 *   const off = delegate(this, 'click', '.btn', (e, target) => { ... });
 *   // later
 *   off();
 */
export function delegate(root, eventType, selector, handler) {
  const listener = (e) => {
    const target = e.target.closest(selector);
    if (target && root.contains(target)) handler(e, target);
  };
  root.addEventListener(eventType, listener);
  return () => root.removeEventListener(eventType, listener);
}

/** Escape a string for safe insertion into an HTML template literal. */
export function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}