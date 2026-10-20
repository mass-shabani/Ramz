-- =====================================================
-- Seed Data for Admin Panel Module — Ramz Project
-- Version 1.0
-- =====================================================
--
-- PURPOSE
-- -------
-- Registers the forms used by the admin_panel module and grants
-- access to admin and manager roles (both with Full condition).
--
-- super-admin is intentionally NOT granted access (per design:
-- super-admin is reserved for the future system-settings module).
--
-- All other roles (guest, user, limit-user, up-user) receive
-- no grants — the admin panel is strictly for admin & manager.
--
-- IDEMPOTENT — safe to run multiple times.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/seed_admin_panel.v1.0.sql
-- =====================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------
-- 1. Forms
-- -----------------------------------------------------
INSERT OR IGNORE INTO form (form_id, form_name, description, enabled) VALUES
('admin_panel.view',          'Admin Panel Access',   'Access to /settings/admin',         1),
('admin_panel.users.manage',  'Manage Users',         'View and edit users',               1),
('admin_panel.forms.manage',  'Manage Forms',         'Create/edit/delete forms',          1),
('admin_panel.access.manage', 'Manage Access Grants', 'Create/edit/delete access grants', 1),
('admin_panel.roles.view',    'View Roles',           'View roles (read-only)',            1);

-- -----------------------------------------------------
-- 2. Grants — admin and manager both Full
-- -----------------------------------------------------
INSERT OR IGNORE INTO form_access (role_id, form_id, condition_id) VALUES
('admin',   'admin_panel.view',          'Full'),
('admin',   'admin_panel.users.manage',  'Full'),
('admin',   'admin_panel.forms.manage',  'Full'),
('admin',   'admin_panel.access.manage', 'Full'),
('admin',   'admin_panel.roles.view',    'Full'),
('manager', 'admin_panel.view',          'Full'),
('manager', 'admin_panel.users.manage',  'Full'),
('manager', 'admin_panel.forms.manage',  'Full'),
('manager', 'admin_panel.access.manage', 'Full'),
('manager', 'admin_panel.roles.view',    'Full');

-- -----------------------------------------------------
-- 3. Verification (optional)
-- -----------------------------------------------------
-- SELECT role_id, form_id, condition_id
-- FROM form_access
-- WHERE form_id LIKE 'admin_panel.%'
-- ORDER BY role_id, form_id;
--
-- Expected: 10 rows (5 for admin, 5 for manager)

-- =====================================================
-- END
-- =====================================================
