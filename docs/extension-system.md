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
| `ui.topbar.center` | `ramz-topbar` | reserved |
| `ui.topbar.start` | `ramz-topbar` | reserved |
| `ui.sidebar.items` | `ramz-sidebar` | reserved |
| `ui.notifications.items` | `ramz-notifications` | reserved |
| `ui.search.items` | `ramz-search` | reserved |

"Reserved" means the point exists in `KNOWN_POINTS` in
`ui_components/extensions.py` but no consumer component reads it yet.

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

Adding a new point: add to `KNOWN_POINTS` in
`ui_components/extensions.py` and wire the consumer component.

## Reserved points — what they will do

When implemented:

- `ui.topbar.center` — content between brand and actions (e.g. search bar).
- `ui.topbar.start` — content just after brand (e.g. page tabs).
- `ui.sidebar.items` — items in `<ramz-sidebar>`'s `<nav>`.
- `ui.notifications.items` — items in `<ramz-notifications>` dropdown.
- `ui.search.items` — results in `<ramz-search>` dropdown.
