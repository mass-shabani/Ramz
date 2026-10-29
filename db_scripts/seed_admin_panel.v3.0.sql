-- =====================================================
-- Seed Data for Admin Panel Module — Ramz Project
-- Version 3.0 (adds admin_panel.users.view_all)
-- =====================================================
--
-- REQUIRES: create_db.v8.0.sql (or v7 + migration_v8_add_rank)
--
-- CHANGELOG v2.0 → v3.0
-- ---------------------
--   * ADDED form: admin_panel.users.view_all
--       - Controls whether a viewer can see users whose role rank
--         is >= their own rank.
--       - Without this grant: the Users list hides equal/higher
--         ranked users entirely (not just blocks editing).
--       - With this grant: everyone is visible (editing is still
--         restricted by rank in admin_panel.services).
--
--   * GRANTS: admin and super-admin receive view_all=1.
--             manager intentionally has NO grant (opt-in via UI).
--
-- IDEMPOTENT — safe to run multiple times.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/seed_admin_panel.v3.0.sql
-- =====================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------
-- 1. Forms
-- -----------------------------------------------------
INSERT OR IGNORE INTO form (form_id, form_name, description, enabled) VALUES
('admin_panel.view',             'Admin Panel Access',   'Access to /settings/admin',                   1),
('admin_panel.users.manage',     'Manage Users',         'View and edit users',                         1),
('admin_panel.users.view_all',   'View All Users',       'See users with equal or higher role rank',    1),
('admin_panel.forms.manage',     'Manage Forms',         'Create/edit/delete forms',                    1),
('admin_panel.access.manage',    'Manage Access Grants', 'Create/edit/delete access grants',            1),
('admin_panel.roles.view',       'View Roles',           'View roles (read-only)',                      1);

-- -----------------------------------------------------
-- 2. Grants — admin and super-admin (level 1)
-- -----------------------------------------------------
-- NOTE: manager deliberately does NOT get admin_panel.users.view_all.
-- This means managers will only see users with role rank < 60.
-- A super-admin can grant it later via the Access Grants UI.
INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
('admin',     'admin_panel.users.view_all', 1),
('super-admin', 'admin_panel.users.view_all', 1);

-- =====================================================
-- END
-- =====================================================
