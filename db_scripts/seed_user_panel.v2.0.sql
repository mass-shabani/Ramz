-- =====================================================
-- Seed Data for User Panel Module — Ramz Project
-- Version 2.0 (level-based, v7 schema)
-- =====================================================
--
-- REQUIRES: create_db.v7.0.sql (or migration_v7)
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/seed_user_panel.v2.0.sql
-- =====================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO form (form_id, form_name, description, enabled) VALUES
('user_panel.view',  'User Panel Access',  'Access to /panel',  1);

INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
('user',        'user_panel.view', 1),
('limit-user',  'user_panel.view', 1),
('up-user',     'user_panel.view', 1),
('manager',     'user_panel.view', 1),
('admin',       'user_panel.view', 1),
('super-admin', 'user_panel.view', 1);

-- =====================================================
-- END
-- =====================================================
