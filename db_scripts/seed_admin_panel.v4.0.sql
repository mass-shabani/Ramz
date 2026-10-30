-- =====================================================
-- Seed Data for Admin Panel Module — Ramz Project
-- Version 4.0 (schema v9 — no form.enabled)
-- =====================================================
--
-- REQUIRES: create_db.v9.0.sql (or v8 + migration_v9_add_locks)
--
-- IDEMPOTENT — safe to run multiple times.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/seed_admin_panel.v4.0.sql
-- =====================================================

PRAGMA foreign_keys = ON;

-- Forms (no `enabled` column in v9; lock defaults to 0)
INSERT OR IGNORE INTO form (form_id, form_name, description) VALUES
('admin_panel.view',             'Admin Panel Access',   'Access to /settings/admin'),
('admin_panel.users.manage',     'Manage Users',         'View and edit users'),
('admin_panel.users.view_all',   'View All Users',       'See users with equal or higher role rank'),
('admin_panel.forms.manage',     'Manage Forms',         'Create/edit/delete forms'),
('admin_panel.access.manage',    'Manage Access Grants', 'Create/edit/delete access grants'),
('admin_panel.roles.view',       'View Roles',           'View roles (read-only)');

-- Grants — admin and manager (level 1); super-admin gets in later seed
INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
('admin',       'admin_panel.view',             1),
('admin',       'admin_panel.users.manage',     1),
('admin',       'admin_panel.users.view_all',   1),
('admin',       'admin_panel.forms.manage',     1),
('admin',       'admin_panel.access.manage',    1),
('admin',       'admin_panel.roles.view',       1),
('manager',     'admin_panel.view',             1),
('manager',     'admin_panel.users.manage',     1),
('manager',     'admin_panel.forms.manage',     1),
('manager',     'admin_panel.access.manage',    1),
('manager',     'admin_panel.roles.view',       1),
('super-admin', 'admin_panel.users.view_all',   1);

-- =====================================================
-- END
-- =====================================================
