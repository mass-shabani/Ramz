# Admin Panel

URL prefix: `/settings/admin`

The admin panel is a page module that gives administrators and managers
a UI to manage users, forms, access grants, and roles. It uses the same
shell (topbar + settings-nav + content-container) as `account_setting`.

## Sections

| Section | URL | Required form |
|---------|-----|---------------|
| Overview | `?section=overview` | `admin_panel.view` |
| Users | `?section=users` | `admin_panel.users.manage` |
| Forms | `?section=forms` | `admin_panel.forms.manage` |
| Access Grants | `?section=access` | `admin_panel.access.manage` |
| Roles | `?section=roles` | `admin_panel.roles.view` |

`admin_panel.view` is required for all sections.

## Route map

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/settings/admin` | Shell (`admin_layout.html`) |
| POST | `/settings/admin/partials/{section}` | HTML partial |
| POST | `/settings/admin/users/list` | JSON: users table |
| POST | `/settings/admin/users/set-role` | Change role |
| POST | `/settings/admin/users/toggle` | Enable/disable |
| POST | `/settings/admin/users/reset-password` | Reset password |
| POST | `/settings/admin/forms/list` | JSON: forms table |
| POST | `/settings/admin/forms/create` | Create form |
| POST | `/settings/admin/forms/update` | Update form |
| POST | `/settings/admin/forms/delete` | Delete form |
| POST | `/settings/admin/access/list` | JSON: grants table |
| POST | `/settings/admin/access/create` | Create grant |
| POST | `/settings/admin/access/update` | Update level |
| POST | `/settings/admin/access/delete` | Delete grant |
| POST | `/settings/admin/roles/list` | JSON: roles table |

All routes require `admin_panel.view`. JSON routes additionally check
their section's `*.manage` (or `*.view`) form.

## Permissions (seed v3.0)

| Form | Granted to |
|------|------------|
| `admin_panel.view` | admin, manager |
| `admin_panel.users.manage` | admin, manager |
| `admin_panel.users.view_all` | admin, super-admin |
| `admin_panel.forms.manage` | admin, manager |
| `admin_panel.access.manage` | admin, manager |
| `admin_panel.roles.view` | admin, manager |

`super-admin` receives its `admin_panel.*` grants in a later seed (v4.0).
Until then, super-admin cannot access the admin panel.

## Rank enforcement

Users actions are gated by rank **in addition to** permissions:

| Action | Rank rule |
|--------|-----------|
| set-role | `current.rank > target.rank` AND `current.rank > new_role.rank` |
| toggle-user | `current.rank > target.rank` |
| reset-password | `current.rank > target.rank` |

Access Grants filtered by rank:

- Dropdowns only list roles with `role.rank < current_rank`.
- List only shows grants for those roles.
- Create/update/delete reject roles with `role.rank >= current_rank`.

Roles view filtered to `role.rank < current_rank`.

Users list visibility:

- Without `admin_panel.users.view_all` → only `role_rank < current_rank`.
- With it → all users visible (editing still rank-restricted).

## Extension usage

The admin panel registers:

- One extension in `ui.user_menu.items` → "Admin Panel" link.
- One extension in `ui.topbar.actions` → "Back to Panel" button.

Both are registered in `admin_panel/module.py` at startup, with a
`form_id`, so `prepare_context` filters them per user.

## JS patterns (admin_layout.html)

- `initUsersPage`, `initFormsPage`, `initAccessPage`, `initRolesPage`.
- Helpers: `showAdminToast`, `apiPost`, `escapeHtml`, `getCurrentSection`.
- One `ramz:table-action` listener per section, with a
  `currentListener` reference to prevent duplicate registrations
  when navigating between sections.
- All dialogs go through `<ramz-dialog id="appDialog">`. No `window.confirm`.

## Data shapes

Users action data attributes:
```
data-action="change-role" data-user-id="<id>"
data-action="toggle-user" data-user-id="<id>" data-enabled="0|1"
data-action="reset-password" data-user-id="<id>"
```

Forms action data attributes:
```
data-action="edit-form" data-form-id="<form_id>"
data-action="delete-form" data-form-id="<form_id>"
```

Access Grants action data attributes:
```
data-action="edit-grant" data-role-id="<rid>" data-form-id="<fid>"
data-action="delete-grant" data-role-id="<rid>" data-form-id="<fid>"
```

Roles action data attributes:
```
data-action="view-grants" data-role-id="<rid>"
```

## Password confirmation

All three user actions (`change-role`, `toggle`, `reset-password`) and all
three grant actions (`create`, `update`, `delete`) and form actions
(`create`, `update`, `delete`) require the admin to re-enter their own
password. The check happens server-side via
`db_service.verify_current_user_password(user_id, password)`.

`reset-password` returns a one-time temporary password in the response.
The client copies it to clipboard and shows it once; the server does
not store it in plaintext.

## Locks (v9.0)

Two lock flags were added in schema v9.0:

| Flag | Meaning | UI |
|------|---------|-----|
| `form.lock` | No grant may be created/updated/deleted for this form | Lock icon in Forms table + Lock column in Access table |
| `role.lock` | No grant may be created/updated/deleted for this role | Lock icon in Roles table + Lock column in Access table |

Important behavior:

- **Locking does not affect enforcement.** Grants still control access
  normally; `form_access.level` is still applied by `has_access`.
- **Locking only blocks grant mutations** (create/update/delete) for
  that entity. It does not block form edit/delete, and does not affect
  users' ability to use the form.
- **Roles have both `enabled` and `lock`.** `role.enabled = 0` disables
  all users with that role (session ejected, login rejected). `role.lock = 1`
  only prevents grant changes.
- **No direct UI for toggling locks yet** — set via SQL:
  ```sql
  UPDATE form SET lock = 1 WHERE form_id = 'admin_panel.view';
  UPDATE role SET lock = 1 WHERE role_id = 'limit-user';
  ```
  `_build_grant_actions` returns [] for grants whose role or form
  is locked, so no Edit/Delete buttons appear.

  Access editor dropdowns show locked roles/forms with a 🔒 suffix
  and the option is disabled.
