# Admin Panel

URL prefix: `/settings/admin`

The admin panel gives administrators and managers a UI to manage users,
forms, access grants, and roles. It uses the same shell (topbar +
settings-nav + content-container) as `account_setting`.

## Sections

| Section | URL | Required grant |
|---------|-----|----------------|
| Overview | `?section=overview` | `admin_panel.view` |
| Users | `?section=users` | `admin_panel.users.manage` |
| Forms | `?section=forms` | `admin_panel.forms.manage` |
| Access Grants | `?section=access` | `admin_panel.access.manage` |
| Roles | `?section=roles` | `admin_panel.roles.view` |

`admin_panel.view` is required for all sections (entry gate).

## Route map

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/settings/admin` | Shell (`admin_layout.html`) |
| POST | `/settings/admin/partials/{section}` | HTML partial |
| POST | `/settings/admin/overview/stats` | JSON: stats + recent users |
| POST | `/settings/admin/users/list` | JSON: users table + assignable roles |
| POST | `/settings/admin/users/set-role` | Change role |
| POST | `/settings/admin/users/toggle` | Enable/disable |
| POST | `/settings/admin/users/reset-password` | Reset password |
| POST | `/settings/admin/forms/list` | JSON: forms table |
| POST | `/settings/admin/forms/create` | Create form |
| POST | `/settings/admin/forms/update` | Update form |
| POST | `/settings/admin/forms/delete` | Delete form |
| POST | `/settings/admin/forms/toggle-lock` | Toggle form lock |
| POST | `/settings/admin/access/list` | JSON: grants table |
| POST | `/settings/admin/access/create` | Create grant |
| POST | `/settings/admin/access/update` | Update level |
| POST | `/settings/admin/access/delete` | Delete grant |
| POST | `/settings/admin/roles/list` | JSON: roles table |
| POST | `/settings/admin/roles/create` | Create role |
| POST | `/settings/admin/roles/update` | Update role |
| POST | `/settings/admin/roles/delete` | Delete role |
| POST | `/settings/admin/roles/toggle-lock` | Toggle role lock |

## Permission model

The admin panel uses a **two-tier** permission model:

1. **Section access** — 6 forms (`*.view` / `*.manage`) gate *visibility* of each section.
2. **Per-button access** — 14 forms (`*.action.*`) gate *individual operations*.

A user with `admin_panel.view` can enter the panel but sees no sections
unless the corresponding section form is granted. Within a section, only
the buttons the user has per-button grants for are rendered.

### Section forms (6)
admin_panel.view
admin_panel.users.manage
admin_panel.users.view_all (see all users, not just lower rank)
admin_panel.forms.manage
admin_panel.access.manage
admin_panel.roles.view

### Per-button forms (14)
admin_panel.users.action.change_role
admin_panel.users.action.toggle
admin_panel.users.action.reset_password

admin_panel.forms.action.create
admin_panel.forms.action.edit
admin_panel.forms.action.delete
admin_panel.forms.action.lock

admin_panel.access.action.create
admin_panel.access.action.edit
admin_panel.access.action.delete

admin_panel.roles.action.create
admin_panel.roles.action.edit
admin_panel.roles.action.delete
admin_panel.roles.action.lock

### Default grants (seed v5.0)

| Role | Section grants | Per-button grants |
|------|----------------|-------------------|
| `super-admin` | all 6 | all 14 |
| `admin` | users, users.view_all, forms, access, roles | users.toggle, users.reset_password |
| `manager` | users, forms, access, roles | users.toggle, users.reset_password |
| `system-admin` | — | — (reserved for system_settings) |

**`admin` / `manager` cannot:** change roles, create/edit/delete forms, create/edit/delete grants, create/edit/delete roles, or toggle locks. They are view-only for those surfaces.

`admin_panel.users.view_all` controls *visibility* of equal/higher-ranked
users. Without it, a viewer sees only users whose role rank is strictly
lower than theirs.

## Overview stats

`POST /settings/admin/overview/stats` returns:

```json
{
  "stats": {
    "users":  15,
    "forms":  32,
    "grants": 40,
    "roles":  4
  },
  "recent_users": [
    {
      "user_id": 5,
      "username": "alice",
      "full_name": "Alice Smith",
      "initials": "AS",
      "email": "alice@example.com",
      "role_name": "user",
      "enabled": true,
      "created_at": "2026-10-30T12:00:00"
    }
  ]
}
```
stats fields are null when the viewer lacks the corresponding
section's .manage / .view grant. grants is scoped to visible
roles (rank < current_rank). roles count is also rank-scoped.

recent_users respects view_all + rank visibility, and is capped at 5.

Rank enforcement
Users actions are gated by rank in addition to permissions:

Action	Rank rule
set-role	current.rank > target.rank AND current.rank > new_role.rank
toggle-user	current.rank > target.rank
reset-password	current.rank > target.rank
Access Grants filtered by rank:

Dropdowns only list roles with role.rank < current.rank.

List only shows grants for those roles.

Create/update/delete reject roles with role.rank >= current.rank.

Roles CRUD gated by rank:

create: current.rank > new_rank

update: current.rank > old_rank AND current.rank > new_rank

delete: current.rank > role.rank

toggle-lock: current.rank > role.rank

Roles view filtered to role.rank < current_rank.

Users list visibility:

Without admin_panel.users.view_all → only role_rank < current_rank.

With it → all users visible (editing still rank-restricted).

Locks (v9.0)
Flag	Meaning	UI
form.lock	No grant may be created/updated/deleted for this form	Lock icon in Forms column + Lock icon in Access actions (replaces buttons)
role.lock	No grant may be created/updated/deleted for this role	Lock icon in Roles column + Lock icon in Access actions (replaces buttons)
Important behavior:

Locking does not affect enforcement. Grants still control access
normally; form_access.level is still applied by has_access.

Locking only blocks grant mutations for that entity. It does not
block form/role edit/delete, and does not affect users' ability to
use the form.

Roles have both enabled and lock. role.enabled = 0 disables
all users with that role (session ejected, login rejected). role.lock = 1
only prevents grant changes.

No UI toggle for form/role lock outside Actions column. Lock/unlock
via the lock icon in the corresponding table's Actions column (requires
password confirm).

_build_*_actions returns [] (or a plain lock icon) for rows
whose associated entity is locked.

Enable vs Lock (Roles)
Field	Where changed	Effect
role.enabled	Roles editor (checkbox)	All users with this role are treated as disabled (login rejected, session ejected within 15s)
role.lock	Roles Actions column (lock icon)	Grants for this role are frozen (no create/edit/delete)
The distinction is deliberate:

enabled is a user-impacting flag → lives in the editor.

lock is an admin-impacting flag → lives in the actions column.

JS patterns (admin_layout.html)
initOverviewPage, initUsersPage, initFormsPage, initAccessPage,
initRolesPage.

Helpers: showAdminToast, apiPost, escapeHtml, getCurrentSection.

One ramz:table-action listener per section, with a currentListener
reference to prevent duplicate registrations when navigating between
sections. Same pattern for Overview (no listener needed — just a fetch).

All dialogs go through <ramz-dialog id="appDialog">. No window.confirm.

Per-button actions are rendered dynamically based on has_access
flags computed server-side and included in actions column.

Data shapes
Users action data attributes:

data-action="change-role"     data-user-id="<id>"
data-action="toggle-user"     data-user-id="<id>"  data-enabled="0|1"
data-action="reset-password"  data-user-id="<id>"
Forms action data attributes:

data-action="edit-form"        data-form-id="<form_id>"
data-action="delete-form"      data-form-id="<form_id>"
data-action="toggle-form-lock" data-form-id="<form_id>"  data-locked="0|1"
data-action="view-form-grants" data-form-id="<form_id>"
Access Grants action data attributes:

data-action="edit-grant"     data-role-id="<rid>"  data-form-id="<fid>"
data-action="delete-grant"   data-role-id="<rid>"  data-form-id="<fid>"
Roles action data attributes:

data-action="edit-role"         data-role-id="<rid>"
data-action="delete-role"       data-role-id="<rid>"
data-action="toggle-role-lock"  data-role-id="<rid>"  data-locked="0|1"
data-action="view-grants"       data-role-id="<rid>"
Lock icon (locked Access row) uses action="" + plain: true →
rendered as <span>, non-interactive.

Password confirmation
All destructive or mutation actions require the admin to re-enter their
own password. The check happens server-side via
db_service.verify_current_user_password(user_id, password).

Sensitive actions:

Users: set-role, toggle, reset-password

Forms: create, update, delete, toggle-lock

Access: create, update, delete

Roles: create, update, delete, toggle-lock

reset-password returns a one-time temporary password in the response.
The client copies it to clipboard and shows it once; the server does
not store it in plaintext.

Feature matrix (Gen 2 complete)
Capability	super-admin	admin	manager
Enter admin panel	✅	✅	✅
Overview stats	✅ all	✅ scoped	✅ scoped
Users: view	✅ all	✅ all (view_all)	✅ rank<self
Users: toggle/reset	✅	✅	✅
Users: change role	✅	❌	❌
Forms: view	✅	✅	✅
Forms: create/edit/delete/lock	✅	❌	❌
Access: view	✅	✅	✅
Access: create/edit/delete	✅	❌	❌
Roles: view	✅	✅	✅
Roles: create/edit/delete/lock	✅	❌	❌
