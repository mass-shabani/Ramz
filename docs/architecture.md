# Architecture

## Layers
Browser
└─ Web Components (native HTMLElement, Light DOM)
│ HTTP / AJAX
▼
Massir Framework
└─ FastAPI router, hooks, run-order groups
│
▼
Application modules
└─ Services, routes, templates
│
▼
system_database
│
▼
SQLite (PostgreSQL / MySQL ready)

## Module categories

Ramz has two kinds of modules.

### Service modules

Provide capabilities used by other modules. No user-facing pages.

| Module | Provides |
|--------|----------|
| `system_logger` | `core_logger` |
| `system_database` | `database_service`, `database_types` |
| `network_fastapi` | `http_api` |
| `template_service` | `template_service`, `menu_manager`, `asset_service` |
| `ui_components` | `component_service`, `ui_hooks` |
| `message_view` | `message_service` |
| `db_manager` | `app_db_service` |
| `route_manager` | (infrastructure) |
| `server_manager` | (infrastructure) |

### Page modules

Serve user-facing pages.

| Module | Provides | URL |
|--------|----------|-----|
| `home` | — | `/` |
| `auth` | `auth_service` | `/login`, `/signup` |
| `user_panel` | `panel_service` | `/panel` |
| `user_profile` | — | `/profile` |
| `account_setting` | — | `/settings/account` |
| `admin_panel` | `admin_panel_service` | `/settings/admin` |

## Startup sequence

1. Massir loads `app_settings.json`.
2. Modules start in the order declared in `modules[].names`.
3. Each module's `start(context)` registers services into
   `context.services`.
4. After all modules started, Massir fires
   `SystemHook.ON_ALL_MODULES_STARTED`.
5. `ui_components` responds by firing `HOOK_COLLECT` — a chance for
   late modules to batch-register extensions.
6. The FastAPI app begins serving requests.

## Request flow (full page)
GET /settings/admin
→ admin_view(request)
→ _ensure_authenticated (session, enabled, revoked)
→ _has_admin_access (form: admin_panel.view)
→ db_service.get_full_profile(user_id)
→ component_service.prepare_context(
template_context=context,
points=["ui.user_menu.items", "ui.topbar.actions"],
user_id=user_id,
db_service=db_service,
app=app,
)
→ template_service.render("admin_layout.html", context)

`prepare_context` injects `ui_extensions` into the template context;
`base.html` serializes it into `window.__ramz.extensions` for the browser.

## Request flow (AJAX partial)
click nav item
→ ramz:load-content event
→ content-container fetches POST /settings/admin/partials/users
→ admin_partial(request, "users")
→ _ensure_authenticated
→ _has_admin_access
→ db_service.get_full_profile
→ permissions dict (has_access for each)
→ component_service.prepare_context
→ render partials/users.html
→ content-container injects HTML
→ ramz:content-loaded event
→ page JS re-initializes the section's table/actions

## Request flow (mutation)

All admin mutations follow the same pattern:

1. Browser: `appDialog.confirm()` + `appDialog.passwordConfirm()`.
2. Browser: POST JSON to `/settings/admin/<resource>/<action>`.
3. Server: `_ensure_authenticated` → permission check →
   `_verify_admin_password` → service method.
4. Service: rank enforcement + business logic.
5. Server: returns `{status, message, ...}` with HTTP 200
   (client checks `data.status`, not `resp.ok`).
6. Browser: `showAdminToast()` or `appDialog.alert()`, then reload table.

## Key design rules

1. Every module exposes itself via `context.services.set(name, ...)`.
2. No module imports another module directly.
3. `db_manager` is the only module that talks to the database.
4. `ui_components` is the only module that ships browser JS.
5. `template_service` is the only module that renders Jinja templates.
6. Access is declarative: `form_id` on routes, `level` in `form_access`.
7. Rank is declarative: `role.rank` in DB, compared at service layer.
