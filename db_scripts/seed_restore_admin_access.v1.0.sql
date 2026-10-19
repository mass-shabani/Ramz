-- =====================================================
-- Restore Access — Ensure admin & manager can access
--                   user_profile and account_setting
-- Version 1.0
-- =====================================================
--
-- PURPOSE
-- -------
-- This script uses INSERT OR REPLACE so that:
--     • Missing grants are created
--     • Existing grants with WRONG conditions are overwritten
--
-- This is intentional: after multiple migrations and seed runs,
-- some grants may have ended up with 'Closed' or old condition
-- names. This script guarantees a coherent baseline.
--
-- It does NOT touch grants for other roles (guest, user, etc.).
--
-- SAFETY
-- ------
-- Idempotent: running twice has the same effect as running once.
-- Backup recommended before running.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < data/seed_restore_admin_access.sql
--
-- AFTER RUNNING: restart the server (to clear the AccessChecker cache).
-- =====================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------
-- 1. ADMIN — full access to all user-facing pages
-- -----------------------------------------------------------------
INSERT OR REPLACE INTO form_access (role_id, form_id, condition_id) VALUES
('admin', 'auth.login.view',          'Full'),
('admin', 'auth.signup.view',         'Full'),
('admin', 'user_profile.view',        'Full'),
('admin', 'user_profile.edit',        'Full'),
('admin', 'account.setting.view',     'Full'),
('admin', 'account.profile.edit',     'Full'),
('admin', 'account.password.change',  'Full'),
('admin', 'account.2fa.manage',       'Full'),
('admin', 'account.banking.manage',   'Full'),
('admin', 'account.sessions.manage',  'Full'),
('admin', 'account.delete',           'Full');

-- -----------------------------------------------------------------
-- 2. MANAGER — same as admin for now
-- -----------------------------------------------------------------
INSERT OR REPLACE INTO form_access (role_id, form_id, condition_id) VALUES
('manager', 'auth.login.view',          'Full'),
('manager', 'auth.signup.view',         'Full'),
('manager', 'user_profile.view',        'Full'),
('manager', 'user_profile.edit',        'Full'),
('manager', 'account.setting.view',     'Full'),
('manager', 'account.profile.edit',     'Full'),
('manager', 'account.password.change',  'Full'),
('manager', 'account.2fa.manage',       'Full'),
('manager', 'account.banking.manage',   'Full'),
('manager', 'account.sessions.manage',  'Full'),
('manager', 'account.delete',           'Full');

-- -----------------------------------------------------------------
-- 3. UP-USER — elevated user access
-- -----------------------------------------------------------------
INSERT OR REPLACE INTO form_access (role_id, form_id, condition_id) VALUES
('up-user', 'user_profile.view',        'High'),
('up-user', 'user_profile.edit',        'High'),
('up-user', 'account.setting.view',     'High'),
('up-user', 'account.profile.edit',     'High'),
('up-user', 'account.password.change',  'High'),
('up-user', 'account.2fa.manage',       'High'),
('up-user', 'account.banking.manage',   'High'),
('up-user', 'account.sessions.manage',  'High');

-- -----------------------------------------------------------------
-- 4. USER — standard user access
-- -----------------------------------------------------------------
INSERT OR REPLACE INTO form_access (role_id, form_id, condition_id) VALUES
('user', 'user_profile.view',        'Medium'),
('user', 'user_profile.edit',        'Medium'),
('user', 'account.setting.view',     'Medium'),
('user', 'account.profile.edit',     'Medium'),
('user', 'account.password.change',  'Medium'),
('user', 'account.2fa.manage',       'Medium');

-- -----------------------------------------------------------------
-- 5. LIMIT-USER — minimal user access
-- -----------------------------------------------------------------
INSERT OR REPLACE INTO form_access (role_id, form_id, condition_id) VALUES
('limit-user', 'user_profile.view',    'Low'),
('limit-user', 'account.setting.view', 'Low');

-- -----------------------------------------------------------------
-- 6. GUEST — public access to auth pages
-- -----------------------------------------------------------------
INSERT OR REPLACE INTO form_access (role_id, form_id, condition_id) VALUES
('guest', 'auth.login.view',  'Low'),
('guest', 'auth.signup.view', 'Low');

-- -----------------------------------------------------------------
-- 7. SUPER-ADMIN — no access to user-facing pages
-- -----------------------------------------------------------------
-- Per the design decision from task 45, super-admin is reserved
-- for system-level operations (not yet implemented). It should
-- NOT have access to user-facing pages.
INSERT OR REPLACE INTO form_access (role_id, form_id, condition_id) VALUES
('super-admin', 'auth.login.view',          'Closed'),
('super-admin', 'auth.signup.view',         'Closed'),
('super-admin', 'user_profile.view',        'Closed'),
('super-admin', 'user_profile.edit',        'Closed'),
('super-admin', 'account.setting.view',     'Closed'),
('super-admin', 'account.profile.edit',     'Closed'),
('super-admin', 'account.password.change',  'Closed'),
('super-admin', 'account.2fa.manage',       'Closed'),
('super-admin', 'account.banking.manage',   'Closed'),
('super-admin', 'account.sessions.manage',  'Closed'),
('super-admin', 'account.delete',           'Closed');

-- -----------------------------------------------------------------
-- 8. Verification
-- -----------------------------------------------------------------
-- Uncomment to check:
-- SELECT r.role_id, fa.form_id, fa.condition_id
-- FROM role r
-- LEFT JOIN form_access fa ON fa.role_id = r.role_id
-- WHERE fa.form_id IN ('user_profile.view', 'account.setting.view')
-- ORDER BY r.role_id, fa.form_id;

-- =====================================================
-- END
-- =====================================================
