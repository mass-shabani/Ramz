# Ramz Project — Documentation

Reference documentation for the Ramz project.

## What is Ramz?

Ramz is a modular cryptocurrency web application built on the **Massir**
framework. It combines a Python backend (FastAPI + Jinja2) with a
framework-agnostic frontend (native Web Components — no Lit, no Vue,
no React).

## Documentation index

| File | Purpose |
|------|---------|
| [architecture.md](architecture.md) | Layers, module categories, data flow |
| [access-control.md](access-control.md) | Level + rank authorization, caching |
| [admin-panel.md](admin-panel.md) | Admin panel: 5 sections, routes, permissions |
| [extension-system.md](extension-system.md) | Injecting contributions into shared components |

## Reading order (new developer)

1. **architecture.md** — understand the shape of the project.
2. **access-control.md** — understand how authorization works
   (single most important subsystem).
3. **admin-panel.md** — understand the main administrative surface.
4. **extension-system.md** — understand how to extend shared UI
   without editing component files.

## Current state

| Component | Status |
|-----------|--------|
| Database schema | v10.0 (rank + locks + per-button admin forms) |
| Massir framework | 0.2.0 Alpha |
| Python | 3.13 |
| Frontend | Native Web Components (17 components) |
| Modules | 14 (8 service/infrastructure, 6 pages) |
| Gen 2 (admin_panel) | ✅ Complete |

## Recent capabilities

- **Extension system** — `ui.user_menu.items` and `ui.topbar.actions`
  are populated by `component_service.prepare_context()` per request
  and serialized to `window.__ramz.extensions`.
- **Access model** — `condition_of` removed. `form_access.level`
  is the single source of truth (0 = Closed, ≥1 = Open).
- **Rank system** — `role.rank` enforces hierarchical authorization
  for Users actions, Access Grants, and Roles CRUD.
- **Lock system** — `form.lock` and `role.lock` freeze grant
  mutations on specific entities without affecting access enforcement.
- **Per-button permission model** — 14 granular `*.action.*` forms
  gate individual admin_panel operations (change_role, toggle,
  reset_password, forms create/edit/delete/lock, access create/edit/delete,
  roles create/edit/delete/lock).
- **Admin panel (Gen 2 complete)** — 5 sections (Overview, Users,
  Forms, Access Grants, Roles), all CRUD-complete with lock/enable
  support and rank enforcement.
- **Overview stats** — real-time counts (users, forms, grants, roles)
  and recent registrations, scoped by viewer's grants and rank.

## Gen 2 milestones (admin_panel)

- Users list (search, pagination, dynamic role list)
- Users actions (change role, toggle, reset password)
- Forms CRUD (create/edit/delete, lock toggle)
- Access Grants CRUD (flat view, mini-matrix, level-based, lock-aware)
- Roles CRUD (create/edit/delete, lock toggle, enable toggle)
- Per-button enforcement on every mutation
- Rank-based visibility + editing across all sections
- Lock-based grant freezing

## Conventions

- **Do not** add Lit, Vue, React, or any JS framework.
- **Do not** use Shadow DOM — Light DOM only, all CSS in `style.css`.
- **Do not** import directly between modules — everything goes
  through `context.services`.
- Custom events are namespaced `ramz:*`.
- Custom elements are namespaced `ramz-*`.

## Related documentation (outside `docs/`)

- `task-prompt.md` — rules for AI-assisted task execution.
- `db_scripts/*.sql` — schema and seed scripts (the real source of truth
  for the database).
- `app_settings.json` — module load order, database config, FastAPI config.
