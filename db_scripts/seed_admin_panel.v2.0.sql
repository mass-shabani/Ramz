-- =====================================================
-- Seed Data for Admin Panel Module — Ramz Project
-- Version 2.0 (level-based, v7 schema)
-- =====================================================
--
-- REQUIRES: create_db.v7.0.sql (or migration_v7)
--
-- IDEMPOTENT — safe to run multiple times.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/seed_admin_panel.v2.0.sql
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
-- 2. Grants — admin and manager, level 1 (open)
-- -----------------------------------------------------
-- NOTE: super-admin gets grants in a later task (v3.0).
INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
('admin',   'admin_panel.view',          1),
('admin',   'admin_panel.users.manage',  1),
('admin',   'admin_panel.forms.manage',  1),
('admin',   'admin_panel.access.manage', 1),
('admin',   'admin_panel.roles.view',    1),
('manager', 'admin_panel.view',          1),
('manager', 'admin_panel.users.manage',  1),
('manager', 'admin_panel.forms.manage',  1),
('manager', 'admin_panel.access.manage', 1),
('manager', 'admin_panel.roles.view',    1);

-- =====================================================
-- END
-- =====================================================
