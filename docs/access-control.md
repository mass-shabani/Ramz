# Access Control

Ramz has **two independent authorization dimensions**:

1. **Level** — per (role, form) permission (row in `form_access`).
2. **Rank** — per role numeric hierarchy (`role.rank`), used only for
   "who can modify whom" in the admin panel.

Both must pass. They are enforced separately.

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
```

`required_condition` is deprecated and ignored (kept for backward
compatibility with older routes).

### Tables

| Table | Purpose |
|-------|---------|
| `role` | Roles (super-admin, admin, manager, ...) |
| `form` | Access points (form_id is any string like admin_panel.view) |
| `form_access` | (role_id, form_id) → level |

`condition_of` was removed in v7.0. Its role is now `form_access.level`.

### Helpers (on db_service)

| Method | Returns |
|--------|---------|
| `has_access(user_id, form_id, min_level=1)` | bool |
| `has_public_access(form_id, min_level=1)` | bool (checks guest) |
| `get_form_level(user_id, form_id)` | int (0 if no grant) |
| `get_form_level_by_role(role_id, form_id)` | int |
| `get_public_level(form_id)` | int or None |
| `get_accessible_forms(user_id)` | list[str] |

### Cache

AccessChecker caches three things with TTLs:

| Key | TTL |
|-----|-----|
| user_id → enabled | 15s |
| user_id → role_id | 60s |
| (role_id, form_id) → level | 60s |

### Cache invalidation

Any change to `form_access` must call:

```python
db_service.invalidate_role_cache(role_id)
db_service.invalidate_form_cache(form_id)
```

Any change to a user's role or enabled flag must call:

```python
db_service.invalidate_access_cache(user_id)
```

## Rank

`role.rank` is an integer hierarchy. Higher = more privileged.

Current ranks:

| Role | Rank |
|------|------|
| super-admin | 80 |
| system-admin (reserved) | 70 |
| manager | 60 |
| admin | 50 |
| up-user | 40 |
| user | 30 |
| limit-user | 20 |
| guest | 10 |

### Rules

- A viewer can only modify users with `target.role_rank < current_rank`.
- A viewer can only grant/revoke access for roles with `role.rank < current_rank`.
- A viewer can only see roles with `role.rank < current_rank`.

Users-list visibility depends on `admin_panel.users.view_all`:

- Without it → only users with `role_rank < current_rank` visible.
- With it → everyone visible (editing still rank-restricted).

Rank is not applied by `has_access` — it is enforced separately at
the service layer in `AdminPanelService.set_user_role`,
`toggle_user`, `reset_password`, `create_grant`,
`update_grant_level`, `delete_grant`.

### Helpers (on db_service)

| Method | Returns |
|--------|---------|
| `get_user_rank(user_id)` | int (0 if no role) |

### Common error codes

| Code | Meaning |
|------|---------|
| `no_permission` | `has_access` returned False |
| `insufficient_rank` | Rank rule failed |
| `invalid_password` | Wrong password for a sensitive action |
| `session_expired` | Session no longer valid |
| `not_found` | Target resource does not exist |

## Extending

To add a new permission:

1. Add a row in `form` (migration or seed).
2. Add grants in `form_access` for the relevant roles.
3. In the route handler, call `has_access(user_id, "<form_id>")`.
4. In the template, hide UI if `has_access` returned False.

Do not add `if user.role == ...` checks in routes. Access is always
driven by `form_access` grants.

## Locks vs. Level vs. Rank

Three independent axes:

| Axis | Field | Enforcement |
|------|-------|-------------|
| **Level** | `form_access.level` | `has_access(user_id, form_id, min_level)` |
| **Rank** | `role.rank` | service layer, `current.rank > target.rank` |
| **Lock** | `form.lock`, `role.lock` | service layer, blocks grant CRUD only |

Notes:

- **Lock does not change `has_access`.** A locked form still respects
  its grants. Locking a form does not revoke anyone's access; it only
  freezes the grants themselves.
- **Lock does not affect user sessions.** Only `role.enabled = 0` does
  (via `is_enabled` JOIN, ejected within 15s).
- **Lock is enforced in `AdminPanelService.create_grant`,
  `update_grant_level`, `delete_grant`.** Error codes:
  `form_locked`, `role_locked`.
- **A super-admin may still need to bypass lock.** Currently there is
  no bypass — locking is absolute from the admin panel. If a lock must
  be broken, do it via SQL and re-lock after.
