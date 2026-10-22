-- =====================================================
-- Seed Data for User Panel Module — Ramz Project
-- Version 1.0
-- =====================================================
--
-- PURPOSE
-- -------
-- Registers the "user_panel.view" form used by the user_panel module
-- and grants access to all authenticated roles.
--
-- Design:
--   • guest has NO access (guest = unauthenticated visitors)
--   • All other roles (user, limit-user, up-user, manager, admin,
--     super-admin) receive Full access to /panel
--
-- IDEMPOTENT — safe to run multiple times.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/seed_user_panel.v1.0.sql
-- =====================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------
-- 1. Form
-- -----------------------------------------------------
INSERT OR IGNORE INTO form (form_id, form_name, description, enabled) VALUES
('user_panel.view',  'User Panel Access',  'Access to /panel',  1);

-- -----------------------------------------------------
-- 2. Grants — all authenticated roles, Full
-- -----------------------------------------------------
INSERT OR IGNORE INTO form_access (role_id, form_id, condition_id) VALUES
('user',        'user_panel.view', 'Medium'),
('limit-user',  'user_panel.view', 'Low'),
('up-user',     'user_panel.view', 'High'),
('manager',     'user_panel.view', 'Full'),
('admin',       'user_panel.view', 'Full'),
('super-admin', 'user_panel.view', 'Closed');

-- -----------------------------------------------------
-- 3. Verification (optional)
-- -----------------------------------------------------
-- SELECT role_id, form_id, condition_id
-- FROM form_access
-- WHERE form_id = 'user_panel.view'
-- ORDER BY role_id;
--
-- Expected: 6 rows

-- =====================================================
-- END
-- =====================================================
