-- =====================================================
-- Database Schema for SQLite - Ramz Project
-- Standardized Structure with Contact-People-User Pattern
-- Version 6.0 (Idempotent, corrected structure)
-- =====================================================
--
-- IDEMPOTENCY
-- -----------
-- This script is FULLY IDEMPOTENT. It can be run multiple times
-- against the same database without side effects. It only creates
-- missing tables, indexes, and default data. Existing schema and
-- data are never modified, dropped, or truncated.
--
-- HOW TO RUN (fresh database)
-- ---------------------------
--   sqlite3 data/rmz_data.db < data/create_db.sql
--
-- HOW TO MIGRATE AN EXISTING DATABASE
-- -----------------------------------
-- Existing databases created with v4.1/v5.0 have a DIFFERENT
-- structure for `user`, `people`, `bank_account`, and the log
-- tables. A dedicated migration file is required; running this
-- file on such databases will NOT fix them.
--
-- CHANGELOG v5.0 → v6.0
-- ---------------------
--   * Restored user.email_id, phone_id, subscription_id,
--     xp_points, two_factor_enabled, two_factor_secret,
--     two_factor_backup_codes (reverted accidental removal)
--   * Restored user.username NOT NULL UNIQUE
--   * Restored people.enabled, NOT NULL names, gender CHECK
--   * Removed people.nationality (not in original schema)
--   * Restored bank_account.contact_id (was people_id)
--   * email_verification now references email(email_id)
--     (was user.user_id)
--   * Merged login_log + user_action_log + user_activity_log
--     into a single user_activity_log table
--   * Corrected seed data: super-admin closed for all
--     user-facing features; up-user no auth access;
--     Super-access condition reserved, not granted
--
-- FUTURE MIGRATION NOTE
-- ---------------------
-- The verification tables (email_verification, phone_verification)
-- and the merged user_activity_log are designed to be moved to a
-- NoSQL store (e.g., MongoDB, Redis) in the future because:
--   * Verification tokens are short-lived, high-write, low-read
--   * Activity logs are append-only and can grow unbounded
-- The schema keeps these tables isolated so that future migration
-- won't require changes to the relational core.
-- =====================================================

PRAGMA foreign_keys = ON;

-- =====================================================
-- 1. LOOKUP & REFERENCE TABLES
-- =====================================================

CREATE TABLE IF NOT EXISTS role (
    role_id     TEXT PRIMARY KEY,
    role_name   TEXT NOT NULL,
    description TEXT,
    enabled     INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS condition_of (
    condition_id   TEXT PRIMARY KEY,
    condition_name TEXT NOT NULL,
    description    TEXT,
    enabled        INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS form (
    form_id     TEXT PRIMARY KEY,
    form_name   TEXT NOT NULL UNIQUE,
    description TEXT,
    enabled     INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS bank (
    bank_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name  TEXT NOT NULL,
    bank_code  TEXT UNIQUE,
    swift_code TEXT,
    enabled    INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS subscription (
    subscription_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_name TEXT NOT NULL UNIQUE,
    description       TEXT,
    price             INTEGER DEFAULT 0,
    duration_days     INTEGER,
    features          TEXT,
    enabled           INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activity_type (
    activity_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name        TEXT NOT NULL UNIQUE,
    description      TEXT,
    enabled          INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS address_type (
    address_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name       TEXT NOT NULL UNIQUE,
    description     TEXT,
    enabled         INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS phone_type (
    phone_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name     TEXT NOT NULL UNIQUE,
    description   TEXT,
    enabled       INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1))
);

-- =====================================================
-- 2. CORE CONTACT HUB
-- =====================================================

CREATE TABLE IF NOT EXISTS contact (
    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enabled    INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 3. PEOPLE TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS people (
    people_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id    INTEGER NOT NULL,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    national_code TEXT UNIQUE,
    birth_date    DATE,
    gender        TEXT CHECK(gender IN ('male', 'female', 'other')),
    enabled       INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contact(contact_id) ON DELETE CASCADE
);

-- =====================================================
-- 4. USER CREDENTIALS & AUDIT
-- =====================================================

CREATE TABLE IF NOT EXISTS user (
    user_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    people_id              INTEGER NOT NULL UNIQUE,
    role_id                TEXT,
    subscription_id        INTEGER,
    email_id               INTEGER,
    phone_id               INTEGER,
    username               TEXT NOT NULL UNIQUE,
    password_hash          TEXT NOT NULL,
    xp_points              INTEGER DEFAULT 0,
    two_factor_enabled     INTEGER NOT NULL DEFAULT 0 CHECK(two_factor_enabled IN (0, 1)),
    two_factor_secret      TEXT,
    two_factor_backup_codes TEXT,
    enabled                INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (people_id) REFERENCES people(people_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id)   REFERENCES role(role_id),
    FOREIGN KEY (subscription_id) REFERENCES subscription(subscription_id),
    FOREIGN KEY (email_id)  REFERENCES email(email_id),
    FOREIGN KEY (phone_id)  REFERENCES phone(phone_id)
);

-- =====================================================
-- MERGED ACTIVITY LOG
-- -----------------------------------------------------
-- One table replaces three previous tables:
--   • login_log        (success/failure of logins)
--   • user_action_log  (arbitrary user actions on entities)
--   • user_activity_log (structured events with type)
--
-- The `activity_type_id` provides the type. Optional columns
-- carry context for specific event kinds:
--   * `success`      — only set for login events
--   * `entity_type`,
--     `entity_id`    — only set for action events
--   * `details`      — optional JSON payload for extra context
--
-- FUTURE: This table is append-only and expected to grow large.
-- It can be moved to a NoSQL store (MongoDB, ClickHouse, etc.)
-- in the future without affecting the relational core.
-- =====================================================

CREATE TABLE IF NOT EXISTS user_activity_log (
    activity_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    activity_type_id INTEGER NOT NULL,
    ip_address       TEXT,
    user_agent       TEXT,
    success          INTEGER CHECK(success IN (0, 1)),
    entity_type      TEXT,
    entity_id        INTEGER,
    details          TEXT,
    action_time      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)          REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (activity_type_id) REFERENCES activity_type(activity_type_id)
);

CREATE TABLE IF NOT EXISTS form_access (
    role_id      TEXT NOT NULL,
    form_id      TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    PRIMARY KEY (role_id, form_id),
    FOREIGN KEY (role_id)      REFERENCES role(role_id),
    FOREIGN KEY (form_id)      REFERENCES form(form_id),
    FOREIGN KEY (condition_id) REFERENCES condition_of(condition_id)
);

CREATE TABLE IF NOT EXISTS user_session (
    session_id   TEXT PRIMARY KEY,
    user_id      INTEGER NOT NULL,
    ip_address   TEXT,
    user_agent   TEXT,
    device_label TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at   DATETIME,
    revoked      INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0, 1)),
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

-- =====================================================
-- 5. CONTACT INFORMATION
-- =====================================================

CREATE TABLE IF NOT EXISTS phone (
    phone_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id     INTEGER NOT NULL,
    phone_number   TEXT NOT NULL,
    phone_type_id  INTEGER NOT NULL DEFAULT 1,
    is_verified    INTEGER NOT NULL DEFAULT 0 CHECK(is_verified IN (0, 1)),
    enabled        INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id)    REFERENCES contact(contact_id) ON DELETE CASCADE,
    FOREIGN KEY (phone_type_id) REFERENCES phone_type(phone_type_id)
);

CREATE TABLE IF NOT EXISTS post_address (
    address_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id       INTEGER NOT NULL,
    address_line1    TEXT NOT NULL,
    address_line2    TEXT,
    city             TEXT,
    state_province   TEXT,
    postal_code      TEXT,
    country          TEXT DEFAULT 'Iran',
    address_type_id  INTEGER NOT NULL DEFAULT 1,
    enabled          INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id)       REFERENCES contact(contact_id) ON DELETE CASCADE,
    FOREIGN KEY (address_type_id)  REFERENCES address_type(address_type_id)
);

CREATE TABLE IF NOT EXISTS email (
    email_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id    INTEGER NOT NULL,
    email_address TEXT NOT NULL,
    is_verified   INTEGER NOT NULL DEFAULT 0 CHECK(is_verified IN (0, 1)),
    enabled       INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contact(contact_id) ON DELETE CASCADE
);

-- =====================================================
-- 6. VERIFICATION TOKENS
-- -----------------------------------------------------
-- Separate from `email.is_verified` and `phone.is_verified`:
--   * is_verified: permanent outcome flag
--   * verification: short-lived process (token + expiry + used)
--
-- FUTURE: These tables are short-lived, high-write, low-read.
-- They can be moved to a NoSQL store (e.g., Redis with TTL)
-- in the future without affecting the relational core.
-- =====================================================

CREATE TABLE IF NOT EXISTS email_verification (
    verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id        INTEGER NOT NULL,
    token           TEXT NOT NULL UNIQUE,
    expires_at      DATETIME NOT NULL,
    used            INTEGER NOT NULL DEFAULT 0 CHECK(used IN (0, 1)),
    FOREIGN KEY (email_id) REFERENCES email(email_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS phone_verification (
    verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_id        INTEGER NOT NULL,
    token           TEXT NOT NULL UNIQUE,
    expires_at      DATETIME NOT NULL,
    used            INTEGER NOT NULL DEFAULT 0 CHECK(used IN (0, 1)),
    FOREIGN KEY (phone_id) REFERENCES phone(phone_id) ON DELETE CASCADE
);

-- =====================================================
-- 7. BANKING INFORMATION
-- =====================================================

CREATE TABLE IF NOT EXISTS bank_account (
    bank_account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id      INTEGER NOT NULL,
    bank_id         INTEGER NOT NULL,
    account_number  TEXT NOT NULL,
    account_name    TEXT NOT NULL,
    iban            TEXT UNIQUE,
    enabled         INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contact(contact_id) ON DELETE CASCADE,
    FOREIGN KEY (bank_id)    REFERENCES bank(bank_id)
);

CREATE TABLE IF NOT EXISTS bank_card (
    bank_card_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_account_id  INTEGER NOT NULL,
    card_number      TEXT NOT NULL,
    card_holder_name TEXT NOT NULL,
    expiry_date      TEXT,
    enabled          INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bank_account_id) REFERENCES bank_account(bank_account_id) ON DELETE CASCADE,
    UNIQUE(bank_account_id, card_number)
);

-- =====================================================
-- 8. INDEXES
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_contact_enabled ON contact(enabled);
CREATE INDEX IF NOT EXISTS idx_people_contact_id ON people(contact_id);
CREATE INDEX IF NOT EXISTS idx_people_national_code ON people(national_code);
CREATE INDEX IF NOT EXISTS idx_user_people_id ON user(people_id);
CREATE INDEX IF NOT EXISTS idx_user_username ON user(username);
CREATE INDEX IF NOT EXISTS idx_user_role_id ON user(role_id);
CREATE INDEX IF NOT EXISTS idx_user_enabled ON user(enabled);
CREATE INDEX IF NOT EXISTS idx_user_email_id ON user(email_id);
CREATE INDEX IF NOT EXISTS idx_user_phone_id ON user(phone_id);
CREATE INDEX IF NOT EXISTS idx_user_subscription_id ON user(subscription_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_type_id ON user_activity_log(activity_type_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_time ON user_activity_log(action_time);
CREATE INDEX IF NOT EXISTS idx_email_verification_email_id ON email_verification(email_id);
CREATE INDEX IF NOT EXISTS idx_email_verification_token ON email_verification(token);
CREATE INDEX IF NOT EXISTS idx_phone_verification_phone_id ON phone_verification(phone_id);
CREATE INDEX IF NOT EXISTS idx_phone_verification_token ON phone_verification(token);
CREATE INDEX IF NOT EXISTS idx_user_session_user_id ON user_session(user_id);
CREATE INDEX IF NOT EXISTS idx_user_session_expires ON user_session(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_session_revoked ON user_session(revoked);
CREATE INDEX IF NOT EXISTS idx_phone_contact_id ON phone(contact_id);
CREATE INDEX IF NOT EXISTS idx_phone_type_id ON phone(phone_type_id);
CREATE INDEX IF NOT EXISTS idx_post_address_contact_id ON post_address(contact_id);
CREATE INDEX IF NOT EXISTS idx_post_address_type_id ON post_address(address_type_id);
CREATE INDEX IF NOT EXISTS idx_email_contact_id ON email(contact_id);
CREATE INDEX IF NOT EXISTS idx_bank_account_contact_id ON bank_account(contact_id);
CREATE INDEX IF NOT EXISTS idx_bank_account_bank_id ON bank_account(bank_id);
CREATE INDEX IF NOT EXISTS idx_bank_card_bank_account_id ON bank_card(bank_account_id);
CREATE INDEX IF NOT EXISTS idx_form_access_role_id ON form_access(role_id);
CREATE INDEX IF NOT EXISTS idx_form_access_condition_id ON form_access(condition_id);

-- =====================================================
-- 9. DEFAULT DATA
-- =====================================================

-- 9.1 Roles
INSERT OR IGNORE INTO role (role_id, role_name, description, enabled) VALUES
('super-admin', 'super-admin', 'System super administrator with access to system settings.', 1),
('admin',       'admin',       'App administrator with full access',                        1),
('manager',     'manager',     'Manager with limited administrative access',                1),
('up-user',     'up-user',     'Regular user with higher than usual access',                1),
('user',        'user',        'Regular user with basic access',                            1),
('limit-user',  'limit-user',  'Regular user with limited access',                          1),
('guest',       'guest',       'Guest user with general access',                            1);

-- 9.2 Conditions
-- NOTE: `Super-access` is reserved for the future system-settings
-- module. It is NOT assigned in any current seed grant.
INSERT OR IGNORE INTO condition_of (condition_id, condition_name, description, enabled) VALUES
('Super-access', 'Super-access', 'Reserved for system settings; super-administrators only', 1),
('Full',         'Full',         'Full access; administrators only',                        1),
('High',         'High',         'Privileged access; up-users',                             1),
('Medium',       'Medium',       'Standard access; regular users',                          1),
('Low',          'Low',          'Basic access; typically for guests',                      1),
('Closed',       'Closed',       'No access; the feature is completely closed',             1);

-- 9.3 Forms
INSERT OR IGNORE INTO form (form_id, form_name, description, enabled) VALUES
('auth.login.view',          'Login page access',     'The /login page',                          1),
('auth.signup.view',         'Signup page access',    'The /signup page',                         1),
('user_profile.view',        'View Profile Page',     'Access to the /profile page',              1),
('user_profile.edit',        'Edit Profile',          'Ability to edit personal information',     1),
('account.setting.view',     'View Account Settings', 'Access to /settings/account',              1),
('account.profile.edit',     'Edit Profile Info',     'Edit personal information',                1),
('account.password.change',  'Change Password',       'Change account password',                  1),
('account.2fa.manage',       'Manage 2FA',            'Enable/disable two-factor authentication', 1),
('account.banking.manage',   'Manage Banking',        'Add/edit/remove bank accounts and cards',  1),
('account.sessions.manage',  'Manage Sessions',       'View and revoke active sessions',          1),
('account.delete',           'Delete Account',        'Delete own account (danger zone)',         1);

-- 9.4 Activity Types
INSERT OR IGNORE INTO activity_type (activity_type_id, type_name, description) VALUES
(1, 'login',             'User login'),
(2, 'logout',            'User logout'),
(3, 'password_change',   'Password change'),
(4, 'profile_update',    'Profile update'),
(5, 'signup',            'Account signup'),
(6, '2fa_enabled',       'Two-factor authentication enabled'),
(7, '2fa_disabled',      'Two-factor authentication disabled'),
(8, 'subscription_change','Subscription plan changed');

-- 9.5 Address Types
INSERT OR IGNORE INTO address_type (address_type_id, type_name, description) VALUES
(1, 'home',     'Home address'),
(2, 'work',     'Work address'),
(3, 'billing',  'Billing address'),
(4, 'shipping', 'Shipping address');

-- 9.6 Phone Types
INSERT OR IGNORE INTO phone_type (phone_type_id, type_name, description) VALUES
(1, 'mobile', 'Mobile phone'),
(2, 'home',   'Home phone'),
(3, 'work',   'Work phone'),
(4, 'fax',    'Fax number');

-- 9.7 Form Access Grants
-- Design intent (per task 45):
--   • guest        : can view auth pages only
--   • limit-user   : can view profile and settings (no edits)
--   • user         : standard user access (own account, no banking)
--   • up-user      : elevated (adds banking and session management)
--   • manager      : full account access (same as admin for now)
--   • admin        : full account access
--   • super-admin  : NO access to user-facing features
--                    (reserved for the future system-settings module)
--
-- Non-guest roles do NOT need auth.* grants because they are
-- already authenticated and are redirected away from /login and
-- /signup by the auth module.

INSERT OR IGNORE INTO form_access (role_id, form_id, condition_id) VALUES
-- Guest
('guest',     'auth.login.view',          'Low'),
('guest',     'auth.signup.view',         'Low'),

-- Limit-user
('limit-user','user_profile.view',        'Low'),
('limit-user','account.setting.view',     'Low'),

-- User
('user',      'user_profile.view',        'Medium'),
('user',      'user_profile.edit',        'Medium'),
('user',      'account.setting.view',     'Medium'),
('user',      'account.profile.edit',     'Medium'),
('user',      'account.password.change',  'Medium'),
('user',      'account.2fa.manage',       'Medium'),

-- Up-user
('up-user',   'user_profile.view',        'High'),
('up-user',   'user_profile.edit',        'High'),
('up-user',   'account.setting.view',     'High'),
('up-user',   'account.profile.edit',     'High'),
('up-user',   'account.password.change',  'High'),
('up-user',   'account.2fa.manage',       'High'),
('up-user',   'account.banking.manage',   'High'),
('up-user',   'account.sessions.manage',  'High'),

-- Manager
('manager',   'user_profile.view',        'Full'),
('manager',   'user_profile.edit',        'Full'),
('manager',   'account.setting.view',     'Full'),
('manager',   'account.profile.edit',     'Full'),
('manager',   'account.password.change',  'Full'),
('manager',   'account.2fa.manage',       'Full'),
('manager',   'account.banking.manage',   'Full'),
('manager',   'account.sessions.manage',  'Full'),
('manager',   'account.delete',           'Full'),

-- Admin
('admin',     'user_profile.view',        'Full'),
('admin',     'user_profile.edit',        'Full'),
('admin',     'account.setting.view',     'Full'),
('admin',     'account.profile.edit',     'Full'),
('admin',     'account.password.change',  'Full'),
('admin',     'account.2fa.manage',       'Full'),
('admin',     'account.banking.manage',   'Full'),
('admin',     'account.sessions.manage',  'Full'),
('admin',     'account.delete',           'Full');

-- Super-admin intentionally has no grants in this seed.
-- When the system-settings module is implemented, its forms will
-- be granted to super-admin with the `Super-access` condition.

-- =====================================================
-- END OF SCHEMA
-- =====================================================