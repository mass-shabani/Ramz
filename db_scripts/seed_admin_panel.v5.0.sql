-- =====================================================
-- Seed Data for Admin Panel Module — Ramz Project
-- Version 5.0 (per-button form_ids + system-admin role)
-- =====================================================
--
-- REQUIRES: schema v9 (create_db.v9.0.sql or migrated)
--
-- CHANGELOG v4.0 → v5.0
-- ---------------------
--   * ADDED role: system-admin (rank=70, reserved for future
--     system_settings module). NO grants.
--   * ADDED 14 per-button forms (see below)
--   * GRANTS (per-buttons only — no base grants repeated):
--       - super-admin: all 14
--       - admin:       users.action.toggle + users.action.reset_password
--       - manager:     users.action.toggle + users.action.reset_password
--
--   NOTE: super-admin base + section grants already exist in the
--   current DB (added manually, equivalent to admin's). This seed
--   only adds super-admin's new per-button grants.
--
--   NOTE: seed v5.0 does NOT enforce per-button checks. Route and
--   service changes come in T75.2 (users), T75.3 (forms), T75.4
--   (access), T75.5 (roles). Until then, admin/manager keep their
--   existing access via admin_panel.{users,forms,access}.manage.
--
-- IDEMPOTENT — safe to run multiple times.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/seed_admin_panel.v5.0.sql
-- =====================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------
-- 1. system-admin role (reserved)
-- -----------------------------------------------------
INSERT OR IGNORE INTO role (role_id, role_name, description, rank, enabled) VALUES
('system-admin', 'system-admin', 'Reserved for the future system_settings module.', 70, 1);

-- -----------------------------------------------------
-- 2. All admin_panel forms (6 section + 14 per-button)
-- -----------------------------------------------------
INSERT OR IGNORE INTO form (form_id, form_name, description) VALUES
-- Section access (enter/view)
('admin_panel.view',             'Admin Panel Access',   'Access to /settings/admin'),
('admin_panel.users.manage',     'Manage Users',         'Access the Users section'),
('admin_panel.users.view_all',   'View All Users',       'See users with equal or higher role rank'),
('admin_panel.forms.manage',     'Manage Forms',         'Access the Forms section'),
('admin_panel.access.manage',    'Manage Access Grants', 'Access the Access Grants section'),
('admin_panel.roles.view',       'View Roles',           'Access the Roles section'),

-- Per-button: Users
('admin_panel.users.action.change_role',    'Change User Role',    'Change another user''s role'),
('admin_panel.users.action.toggle',         'Toggle User Status',  'Enable or disable another user'),
('admin_panel.users.action.reset_password', 'Reset User Password', 'Reset another user''s password'),

-- Per-button: Forms (create/edit/delete + lock)
('admin_panel.forms.action.create',  'Create Form',  'Create new forms'),
('admin_panel.forms.action.edit',    'Edit Form',    'Edit existing forms'),
('admin_panel.forms.action.delete',  'Delete Form',  'Delete forms'),
('admin_panel.forms.action.lock',    'Lock Form',    'Toggle form lock (freeze grants)'),

-- Per-button: Access Grants
('admin_panel.access.action.create', 'Create Grant', 'Create new access grants'),
('admin_panel.access.action.edit',   'Edit Grant',   'Edit grant levels'),
('admin_panel.access.action.delete', 'Delete Grant', 'Delete access grants'),

-- Per-button: Roles (create/edit/delete + lock)
('admin_panel.roles.action.create',  'Create Role',  'Create new roles'),
('admin_panel.roles.action.edit',    'Edit Role',    'Edit existing roles'),
('admin_panel.roles.action.delete',  'Delete Role',  'Delete roles'),
('admin_panel.roles.action.lock',    'Lock Role',    'Toggle role lock (freeze grants)');

-- -----------------------------------------------------
-- 3. Per-button grants
-- -----------------------------------------------------
-- super-admin: all 14 per-buttons
INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
('super-admin', 'admin_panel.users.action.change_role',    1),
('super-admin', 'admin_panel.users.action.toggle',         1),
('super-admin', 'admin_panel.users.action.reset_password', 1),
('super-admin', 'admin_panel.forms.action.create',         1),
('super-admin', 'admin_panel.forms.action.edit',           1),
('super-admin', 'admin_panel.forms.action.delete',         1),
('super-admin', 'admin_panel.forms.action.lock',           1),
('super-admin', 'admin_panel.access.action.create',        1),
('super-admin', 'admin_panel.access.action.edit',          1),
('super-admin', 'admin_panel.access.action.delete',        1),
('super-admin', 'admin_panel.roles.action.create',         1),
('super-admin', 'admin_panel.roles.action.edit',           1),
('super-admin', 'admin_panel.roles.action.delete',         1),
('super-admin', 'admin_panel.roles.action.lock',           1);

-- admin: only toggle + reset (no change_role, no CRUD)
INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
('admin', 'admin_panel.users.action.toggle',         1),
('admin', 'admin_panel.users.action.reset_password', 1);

-- manager: only toggle + reset
INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
('manager', 'admin_panel.users.action.toggle',         1),
('manager', 'admin_panel.users.action.reset_password', 1);

-- =====================================================
-- END
-- =====================================================
