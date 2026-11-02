# Access Control

Ramz has **three independent authorization dimensions**:

1. **Level** — per (role, form) permission (row in `form_access`).
2. **Rank** — per role numeric hierarchy (`role.rank`), used for
   "who can modify whom" in the admin panel.
3. **Lock** — per-form / per-role freeze flag (`form.lock`, `role.lock`),
   blocks grant mutations only.

They are enforced separately. All three must pass for the operation
to proceed (where applicable).

## Level

A grant is a row in `form_access`:
(role_id, form_id) → level INTEGER (≥ 0)

| Level | Meaning |
|-------|---------|
| `0` | Closed — no access, regardless of `min_level` |
| `≥ 1` | Open — access granted if `level >= min_level` |

The caller decides what level to require:

```python
await db_service.has_access(user_id, "admin_panel.view")            # min_level=1
await db_service.has_access(user_id, "admin_panel.view", min_level=2)
required_condition is deprecated and ignored (kept for backward
compatibility with older routes).
```

Tables
Table	Purpose
role	Roles (super-admin, admin, manager, ...)
form	Access points (form_id is any string like admin_panel.view)
form_access	(role_id, form_id) → level
condition_of was removed in v7.0. Its role is now form_access.level.

Helpers (on db_service)
Method	Returns
has_access(user_id, form_id, min_level=1)	bool
has_public_access(form_id, min_level=1)	bool (checks guest)
get_form_level(user_id, form_id)	int (0 if no grant)
get_form_level_by_role(role_id, form_id)	int
get_public_level(form_id)	int or None
get_accessible_forms(user_id)	list[str]
Cache
AccessChecker caches three things with TTLs:

Key	TTL
user_id → enabled	15s
user_id → role_id	60s
(role_id, form_id) → level	60s
Cache invalidation
Any change to form_access must call:

db_service.invalidate_role_cache(role_id)

db_service.invalidate_form_cache(form_id)

Any change to a user's role or enabled flag must call:

db_service.invalidate_access_cache(user_id)

Rank
role.rank is an integer hierarchy. Higher = more privileged.

Current ranks:

Role	Rank
super-admin	80
system-admin (reserved)	70
manager	60
admin	50
up-user	40
user	30
limit-user	20
guest	10
Rules:

A viewer can only modify users with
target.role_rank < current_rank.

A viewer can only grant/revoke access for roles with
role.rank < current_rank.

A viewer can only see roles with role.rank < current_rank.

Users-list visibility depends on admin_panel.users.view_all:

Without it → only users with role_rank < current_rank visible.

With it → everyone visible (editing still rank-restricted).

A viewer can only create/update roles with
new_rank < current_rank.

Rank is not applied by has_access — it is enforced separately at
the service layer in AdminPanelService.set_user_role, toggle_user,
reset_password, create_grant, update_grant_level, delete_grant,
create_role, update_role, delete_role.

Helpers (on db_service)
Method	Returns
get_user_rank(user_id)	int (0 if no role)
Lock
Two flags added in schema v9.0:

Flag	Meaning
form.lock = 1	Grants for this form cannot be created/updated/deleted
role.lock = 1	Grants for this role cannot be created/updated/deleted
Lock is enforced only in:

AdminPanelService.create_grant → returns form_locked / role_locked

AdminPanelService.update_grant_level → same

AdminPanelService.delete_grant → same

Lock does not affect:

has_access — grants still apply.

Form edit/delete.

Role edit/delete/enable.

User behavior.

Locks vs. Level vs. Rank
Axis	Field	Enforcement	Blocks
Level	form_access.level	has_access(user_id, form_id, min_level)	Any unauthorized read/write
Rank	role.rank	service layer, current.rank > target.rank	Admin modifications of equal/higher-ranked entities
Lock	form.lock, role.lock	service layer (grant CRUD only)	Grant mutations on the locked entity
Role enabled vs Lock
role.enabled is a user-impacting flag. When enabled = 0:

All users with that role are treated as disabled.

is_enabled(user_id) returns False (JOINs role).

Session validation fails → ejected on next request (within 15s).

Login is rejected with account_disabled.

role.lock is an admin-impacting flag. When lock = 1:

Grants cannot be created/updated/deleted for this role.

Users still work normally (logins accepted, sessions valid).

Role can still be edited, enabled/disabled, deleted (if no grants/users).

These are orthogonal — a role can be enabled and locked, disabled and
unlocked, or anything in between.

Common error codes
Code	Meaning
no_permission	has_access returned False (or per-button check failed)
insufficient_rank	Rank rule failed
form_locked	Grants for a locked form cannot be modified
role_locked	Grants for a locked role cannot be modified
invalid_password	Wrong password for a sensitive action
session_expired	Session no longer valid
not_found	Target resource does not exist
Extending
To add a new permission:

Add a row in form (migration or seed).

Add grants in form_access for the relevant roles.

In the route handler, call has_access(user_id, "<form_id>").

In the template, hide UI if has_access returned False.

Do not add if user.role == ... checks in routes. Access is always
driven by form_access grants. Rank checks are separate and always use
get_user_rank.

Per-button model (admin_panel)
The admin panel uses a two-tier model (see admin-panel.md):

Section access (*.manage / *.view) — gates visibility.

Per-button access (*.action.*) — gates individual operations.

This lets an admin see, e.g., the Users table without being able to
change roles — by granting users.manage but not
users.action.change_role.
