# Extension System

The extension system lets any module inject entries into shared UI
components (user menu, topbar, etc.) without editing those component
files.

Built on `component_service` (in `ui_components`) and `base.html`
(in `template_service`).

## Active points

| Point | Component | Status |
|-------|-----------|--------|
| `ui.user_menu.items` | `ramz-user-menu` | active |
| `ui.topbar.actions` | `ramz-topbar` | active |
| `ui.sidebar.items` | `ramz-sidebar` | active |
| `ui.dashboard.widgets` | `dashboard-content.html` (partial) | active |
| `ui.account_setting.sections` | `settings.html` (partial) | active |
| `ui.topbar.center` | `ramz-topbar` | reserved |
| `ui.topbar.start` | `ramz-topbar` | reserved |
| `ui.notifications.items` | `ramz-notifications` | reserved |
| `ui.search.items` | `ramz-search` | reserved |

"Reserved" means the point exists in `KNOWN_POINTS` in
`ui_components/extensions.py` but no consumer component reads it yet.

"active" for partial-based points means the Jinja template reads
`ui_extensions[<point>]` and renders the entries. See the "Per-point
consumption details" section below.

## Registering an extension

Inside a module's `start(context)`, after obtaining `component_service`:

```python
component_service.register_extension(
    point="ui.user_menu.items",
    data={
        "label": "Admin Panel",
        "url":   "/settings/admin",
        "icon":  "🛡️",
        "order": 10,
    },
    form_id="admin_panel.view",   # optional; filters per user
    module_name="admin_panel",
)
```

`form_id` is optional. If set, `prepare_context` will filter the entry
using `db_service.has_access(user_id, form_id)` per request.

`data` can also use `{"html": "<a class='um-item' href='...'>...</a>"}`
for full control (rendered raw). Use sparingly.

`ramz-topbar` supports `data.hide_on_path` — if the current path
matches, the action is hidden. Used by user_panel for "Back to Panel"
on `/panel` itself.

## Resolving extensions

Before rendering a page, call `prepare_context`:

```python
context = await component_service.prepare_context(
    template_context=context,
    points=["ui.user_menu.items", "ui.topbar.actions"],
    user_id=user_id,
    db_service=db_service,
    app=app,
)
```

This mutates `context` to add `ui_extensions`:

```python
{
    "ui.user_menu.items": [
        {"label": "Admin Panel", "url": "/settings/admin",
         "icon": "🛡️", "order": 10},
    ],
    "ui.topbar.actions": [...],
}
```

## Client-side consumption

`base.html` serializes `ui_extensions` into `window.__ramz.extensions`:

```html
<script>
window.__ramz = window.__ramz || {};
window.__ramz.extensions = {{ ui_extensions | tojson | safe }};
</script>
```

Components read it:

```javascript
const items = window.__ramz?.extensions?.['ui.user_menu.items'] || [];
```

`ramz-user-menu` renders `{label, url, icon}` as `<a>` elements, or
`{html}` as raw HTML. `ramz-topbar` renders `{href, title, icon}` as
`<a class="icon-btn">`, or `{html}` as raw HTML.

## Per-point consumption details

The three active partial-extension points consume entries slightly
differently. Payload shapes are documented per point.

### `ui.sidebar.items` — consumed by `<ramz-sidebar>`

Consumed in `sidebar.js::_renderExtensions()`, called once from
`connectedCallback` (after the `#bound` guard). The entries are
appended to the existing `<nav class="nav">` **in addition to**
the hardcoded items in `panel_layout.html` (they do not replace
them).

Entry shape:

```python
{
    "label":    "Crypto Coins",           # required; entries with no label are ignored
    "endpoint": "/panel/crypto/coins",    # optional; passed through to <ramz-menu-item>
    "href":     "#",                       # optional; fallback if endpoint is absent
    "icon":     "<svg>...</svg>",         # optional; raw HTML or plain text (innerHTML)
    "order":    100,                       # informational; list is pre-sorted server-side
    "group":    "Crypto",                 # optional; wraps the item in <ramz-menu-group>
}
```

Group behaviour:

- An entry with `group` set is appended inside a `<ramz-menu-group label="...">`.
- An existing group with the same `label` (from `panel_layout.html` or from
  a previous entry in the same render pass) is reused.
- A missing group is created at the end of the `<nav>`.
- Entries without `group` are appended directly to the `<nav>`.

Ordering: the server (`extensions.py::resolve`) sorts entries by
`data.order` before serializing to `window.__ramz.extensions`. The
client preserves the incoming order and does not re-sort.

### `ui.dashboard.widgets` — consumed by `dashboard-content.html`

Rendered server-side by Jinja in
`user_panel/templates/partials/dashboard-content.html`:

```jinja
{% if ui_extensions and ui_extensions['ui.dashboard.widgets'] %}
  {% for widget in ui_extensions['ui.dashboard.widgets'] %}
    {% if widget.html %}{{ widget.html | safe }}{% endif %}
  {% endfor %}
{% endif %}
```

Entry shape:

```python
{
    "html":  "<crypto-top-coins endpoint='/crypto/coins/api/summary'></crypto-top-coins>",
    "order": 10,
}
```

The `html` field is rendered with `|safe` — the registering module is
responsible for producing safe HTML. Common patterns:

- A custom element (e.g. `<crypto-top-coins ...>`) that fetches its own data.
- A server-rendered snippet (rare; prefer the custom element pattern).

The `form_id` filter (if provided at registration) still applies
server-side via `prepare_context` — the widget is not delivered to
users who lack the grant.

### `ui.account_setting.sections` — consumed by `settings.html`

Rendered server-side by Jinja in
`account_setting/templates/settings.html`, in a new
"Connected Services" block placed just above the Danger Zone section:

```jinja
{% if ui_extensions and ui_extensions['ui.account_setting.sections'] %}
<div class="settings-nav-title">Connected Services</div>
{% for item in ui_extensions['ui.account_setting.sections'] %}
<a class="settings-nav-item"
   href="?section={{ item.id }}"
   data-section="{{ item.id }}"
   data-endpoint="{{ item.endpoint }}">
  {% if item.icon %}<span class="settings-nav-icon">{{ item.icon | safe }}</span>{% endif %}
  {{ item.label }}
</a>
{% endfor %}
{% endif %}
```

Entry shape:

```python
{
    "id":       "crypto-providers",                                  # required; used in URL and data-section
    "label":    "Crypto Connections",                                # required
    "endpoint": "/settings/crypto/providers/partials/overview",      # required; content-container fetches this
    "icon":     "<svg>...</svg>",                                    # optional; raw HTML (|safe)
    "order":    10,                                                   # optional; informational
}
```

The `endpoint` field is passed through to the existing
`<content-container>` via the `data-endpoint` attribute — the URL may
be any path on the same origin (including routes served by another
module). `settings.html`'s existing JavaScript handles both internal
(`/settings/account/partials/...`) and external
(`/settings/crypto/providers/partials/...`) endpoints without changes.

**Note on URL state:** because `settings_view` in
`account_setting/routes.py` only knows the built-in
`PARTIAL_TEMPLATES` sections (`personal`, `contact`, `password`,
`twofa`, `subscription`, `banking`, `sessions`, `danger`), reloading
the page with `?section=crypto-providers` currently falls back to
`personal`. This is a known limitation to be addressed when the first
consumer module (crypto_providers) lands — either by extending
`VALID_SECTIONS` dynamically from `ui_extensions`, or by adding an
opt-in partial passthrough for external endpoints.

## Hooks

Two custom hooks are registered in `context.services["ui_hooks"]`:

| Hook | Fired when |
|------|------------|
| `HOOK_COLLECT` | Once, at `ON_ALL_MODULES_STARTED` |
| `HOOK_RESOLVE` | Per request, inside `prepare_context` |

`HOOK_COLLECT` is a chance for late modules to batch-register after all
modules have started. `HOOK_RESOLVE` is for per-request dynamic
contributions (rarely needed).

Modules consume hooks via `context.services.get("ui_hooks")`, not via
imports:

```python
ui_hooks = context.services.get("ui_hooks")
if ui_hooks and app:
    app.register_hook(ui_hooks["collect"], my_collect_callback)
```

## Rules

- Do not import `extensions.py` or `services.py` from another
  module. Use `context.services`.
- `form_id` filters per user, not per role. It uses `has_access`.
- Order is explicit (`data.order`, default 100). Lower = earlier.
- Unknown points are silently rejected and logged with tag="ui".

Adding a new point — the full checklist:

1. Add the point name to `KNOWN_POINTS` in
   `ui_components/extensions.py`.
2. Implement a consumer:
   - **Web Component:** read `window.__ramz.extensions[<point>]` in
     `connectedCallback` (after any state-initialization guards) and
     append children to the appropriate DOM node. Sort client-side only
     if the server did not already sort — see `HooksManager.dispatch`
     for ordering guarantees.
   - **Jinja partial:** read `context["ui_extensions"][<point>]` in the
     template. Call `component_service.prepare_context(...)` with the
     point name from the route handler before rendering.
3. Document the payload shape under "Per-point consumption details"
   in this file.
4. If the point is user-scoped (i.e. should only be delivered to users
   with a specific grant), use the `form_id` argument of
   `register_extension(...)` — access filtering is handled server-side.

Rule: a point may only be added to `KNOWN_POINTS` **after** its
consumer is in place. A registered extension with no consumer silently
does nothing — this is intentional (fail-safe, no crash), but it is
also a silent misconfiguration that is hard to debug. Add the consumer
first, then the point name.

## Reserved points — what they will do

When implemented:

- `ui.topbar.center` — content between brand and actions (e.g. search bar).
- `ui.topbar.start` — content just after brand (e.g. page tabs).
- `ui.notifications.items` — items in `<ramz-notifications>` dropdown.
- `ui.search.items` — results in `<ramz-search>` dropdown.

(`ui.sidebar.items` has moved to active — see the "Per-point
consumption details" section.)
