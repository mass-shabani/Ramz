-- =====================================================
-- Migration 006 — Convert role_id and condition_id to TEXT
-- Version 1.0
-- =====================================================
--
-- PURPOSE
-- -------
-- Rebuilds role, condition_of, user, and form_access tables so that:
--     role.role_id                 becomes TEXT (value = role_name)
--     role.role_name               becomes display label (value = role_name)
--     condition_of.condition_id    becomes TEXT (value = condition_name)
--     condition_of.condition_name  becomes display label
--     user.role_id                 becomes TEXT (FK to role)
--     form_access.role_id          becomes TEXT
--     form_access.condition_id     becomes TEXT
--
-- All existing data is preserved. Foreign key relationships are
-- re-established after the rebuild.
--
-- IMPORTANT
-- ---------
-- THIS IS A ONE-SHOT MIGRATION. Do NOT run it twice.
-- Before running, make a backup:
--   copy data\rmz_data.db data\rmz_data.db.bak
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < data/migration_006_role_condition_text_ids.sql
-- =====================================================

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- =====================================================
-- 1. Rebuild `role`
-- =====================================================

CREATE TABLE role_new (
    role_id     TEXT PRIMARY KEY,
    role_name   TEXT NOT NULL,
    description TEXT,
    enabled     INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO role_new (role_id, role_name, description, enabled, created_at, updated_at)
SELECT role_name, role_name, description, enabled, created_at, updated_at
FROM role;

-- =====================================================
-- 2. Rebuild `condition_of`
-- =====================================================

CREATE TABLE condition_of_new (
    condition_id   TEXT PRIMARY KEY,
    condition_name TEXT NOT NULL,
    description    TEXT,
    enabled        INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1))
);

INSERT INTO condition_of_new (condition_id, condition_name, description, enabled)
SELECT condition_name, condition_name, description, enabled
FROM condition_of;

-- =====================================================
-- 3. Rebuild `user` (role_id INTEGER → TEXT)
-- =====================================================

CREATE TABLE user_new (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    people_id     INTEGER NOT NULL UNIQUE,
    username      TEXT UNIQUE,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role_id       TEXT,
    enabled       INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (people_id) REFERENCES people(people_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id)   REFERENCES role_new(role_id)
);

INSERT INTO user_new (
    user_id, people_id, username, email, password_hash,
    role_id, enabled, created_at, updated_at
)
SELECT
    u.user_id,
    u.people_id,
    u.username,
    u.email,
    u.password_hash,
    (SELECT r.role_name FROM role r WHERE r.role_id = u.role_id),
    u.enabled,
    u.created_at,
    u.updated_at
FROM user u;

-- =====================================================
-- 4. Rebuild `form_access` (both FKs to TEXT)
-- =====================================================

CREATE TABLE form_access_new (
    role_id      TEXT NOT NULL,
    form_id      TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    PRIMARY KEY (role_id, form_id),
    FOREIGN KEY (role_id)      REFERENCES role_new(role_id),
    FOREIGN KEY (form_id)      REFERENCES form(form_id),
    FOREIGN KEY (condition_id) REFERENCES condition_of_new(condition_id)
);

INSERT INTO form_access_new (role_id, form_id, condition_id)
SELECT
    (SELECT r.role_name      FROM role r         WHERE r.role_id      = fa.role_id),
    fa.form_id,
    (SELECT c.condition_name FROM condition_of c WHERE c.condition_id = fa.condition_id)
FROM form_access fa
WHERE fa.role_id IS NOT NULL AND fa.condition_id IS NOT NULL;

-- =====================================================
-- 5. Drop old tables and rename new ones
-- =====================================================

DROP TABLE form_access;
DROP TABLE user;
DROP TABLE role;
DROP TABLE condition_of;

ALTER TABLE role_new         RENAME TO role;
ALTER TABLE condition_of_new RENAME TO condition_of;
ALTER TABLE user_new         RENAME TO user;
ALTER TABLE form_access_new  RENAME TO form_access;

-- =====================================================
-- 6. Recreate indexes
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_user_role_id            ON user(role_id);
CREATE INDEX IF NOT EXISTS idx_form_access_role_id     ON form_access(role_id);
CREATE INDEX IF NOT EXISTS idx_form_access_condition_id ON form_access(condition_id);

COMMIT;

PRAGMA foreign_keys = ON;

-- =====================================================
-- 7. Add NEW roles and conditions (if not already present)
-- =====================================================
-- The migration above only converts existing data. New roles and
-- conditions that were defined in the new create_db.sql seed must
-- be added separately.

INSERT OR IGNORE INTO role (role_id, role_name, description, enabled) VALUES
('super-admin', 'super-admin', 'System super administrator with access to system settings.', 1),
('admin',       'admin',       'App administrator with full access',                        1),
('manager',     'manager',     'Manager with limited administrative access',                1),
('up-user',     'up-user',     'Regular user with higher than usual access',                1),
('user',        'user',        'Regular user with basic access',                            1),
('limite-user', 'limite-user', 'Regular user with limited access',                          1),
('guest',       'guest',       'Guest user with general access',                            1);

INSERT OR IGNORE INTO condition_of (condition_id, condition_name, description, enabled) VALUES
('Super-access', 'Super-access', 'Only app settings access; super-administrators', 1),
('Full',         'Full',         'Full access; administrators only',               1),
('High',         'High',         'Privileged access; up-users',                    1),
('Medium',       'Medium',       'Standard access; regular users',                 1),
('Low',          'Low',          'Basic access; typically for guests',             1),
('Closed',       'Closed',       'No access; the feature is completely closed',    1);

-- =====================================================
-- 8. Add new form_access grants (per new seed)
-- =====================================================
-- Note: existing grants are preserved. New grants from the new seed
-- are added with INSERT OR IGNORE.

INSERT OR IGNORE INTO form (form_id, form_name, description, enabled) VALUES
('auth.login.view',          'Login page access',     'The /login page',                          1),
('auth.signup.view',         'Signup page access',    'The /signup page',                         1),
('user_profile.view',        'View Profile Page',     'Access to the /profile page',              1),
('user_profile.edit',        'Edit Profile',          'Ability to edit personal information',     1),
('account.setting.view',     'View Account Settings', 'Access to /account/settings',              1),
('account.profile.edit',     'Edit Profile Info',     'Edit personal information',                1),
('account.password.change',  'Change Password',       'Change account password',                  1),
('account.2fa.manage',       'Manage 2FA',            'Enable/disable two-factor authentication', 1),
('account.banking.manage',   'Manage Banking',        'Add/edit/remove bank accounts and cards',  1),
('account.sessions.manage',  'Manage Sessions',       'View and revoke active sessions',          1),
('account.delete',           'Delete Account',        'Delete own account (danger zone)',         1);

INSERT OR IGNORE INTO form_access (role_id, form_id, condition_id) VALUES
('up-user',     'auth.login.view',          'Full'),
('up-user',     'auth.signup.view',         'Full'),
('super-admin', 'user_profile.edit',        'Low'),
('super-admin', 'user_profile.view',        'Low'),
('admin',       'user_profile.edit',        'Medium'),
('admin',       'user_profile.view',        'Medium'),
('manager',     'user_profile.edit',        'High'),
('manager',     'user_profile.view',        'High'),
('super-admin', 'account.2fa.manage',       'Low'),
('super-admin', 'account.banking.manage',   'Low'),
('super-admin', 'account.delete',           'Low'),
('super-admin', 'account.password.change',  'Low'),
('super-admin', 'account.profile.edit',     'Low'),
('super-admin', 'account.sessions.manage',  'Low'),
('super-admin', 'account.setting.view',     'Low'),
('admin',       'account.2fa.manage',       'Medium'),
('admin',       'account.banking.manage',   'Medium'),
('admin',       'account.password.change',  'Medium'),
('admin',       'account.profile.edit',     'Medium'),
('admin',       'account.sessions.manage',  'Medium'),
('admin',       'account.setting.view',     'Medium'),
('admin',       'account.delete',           'Super-access'),
('manager',     'account.2fa.manage',       'High'),
('manager',     'account.password.change',  'High'),
('manager',     'account.profile.edit',     'High'),
('manager',     'account.setting.view',     'High'),
('manager',     'account.banking.manage',   'Super-access'),
('manager',     'account.delete',           'Super-access'),
('manager',     'account.sessions.manage',  'Super-access');

-- =====================================================
-- Verification
-- =====================================================
-- SELECT role_id, role_name FROM role ORDER BY role_id;
-- SELECT condition_id FROM condition_of ORDER BY condition_id;
-- SELECT role_id, form_id, condition_id FROM form_access ORDER BY role_id, form_id;
-- SELECT user_id, role_id FROM user;
