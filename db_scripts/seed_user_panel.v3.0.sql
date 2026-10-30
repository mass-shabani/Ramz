-- =====================================================
-- Seed Data for User Panel Module — Ramz Project
-- Version 3.0 (schema v9 — no form.enabled)
-- =====================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO form (form_id, form_name, description) VALUES
('user_panel.view',  'User Panel Access',  'Access to /panel');

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
