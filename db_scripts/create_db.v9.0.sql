-- =====================================================
-- Database Schema for SQLite - Ramz Project
-- Standardized Structure with Contact-People-User Pattern
-- Version 9.0 (Idempotent, level-based + rank + locks)
-- =====================================================
--
-- CHANGELOG v8.0 → v9.0
-- ---------------------
--   * DROPPED: form.enabled (replaced by form.lock for infra)
--   * ADDED: form.lock (INTEGER NOT NULL DEFAULT 0)
--   * ADDED: role.lock (INTEGER NOT NULL DEFAULT 0)
--   * role.enabled KEPT — used to eject users on login
--
-- CHANGELOG v7.0 → v8.0
-- ---------------------
--   * ADDED: role.rank (INTEGER NOT NULL DEFAULT 0)
--       - Numeric hierarchy: super-admin=80, system-admin=70,
--         manager=60, admin=50, up-user=40, user=30,
--         limit-user=20, guest=10
--       - Used for rank-based authorization in admin_panel:
--         a user may only modify users with strictly lower rank
--
-- MIGRATION
-- ---------
-- Existing v7.0 databases MUST run
-- db_scripts/migration_v8_add_rank.sql first.
--
-- =====================================================

PRAGMA foreign_keys = ON;

-- =====================================================
-- 1. LOOKUP & REFERENCE TABLES
-- =====================================================

CREATE TABLE IF NOT EXISTS role (
    role_id     TEXT PRIMARY KEY,
    role_name   TEXT NOT NULL,
    description TEXT,
    rank        INTEGER NOT NULL DEFAULT 0,
    enabled     INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    lock        INTEGER NOT NULL DEFAULT 0 CHECK(lock IN (0, 1)),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS form (
    form_id     TEXT PRIMARY KEY,
    form_name   TEXT NOT NULL UNIQUE,
    description TEXT,
    lock        INTEGER NOT NULL DEFAULT 0 CHECK(lock IN (0, 1))
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
    role_id TEXT NOT NULL,
    form_id TEXT NOT NULL,
    level   INTEGER NOT NULL DEFAULT 1 CHECK(level >= 0),
    PRIMARY KEY (role_id, form_id),
    FOREIGN KEY (role_id) REFERENCES role(role_id),
    FOREIGN KEY (form_id) REFERENCES form(form_id)
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

-- =====================================================
-- 9. DEFAULT DATA
-- =====================================================

-- 9.1 Roles (with rank for hierarchy)
INSERT OR IGNORE INTO role (role_id, role_name, description, rank, enabled) VALUES
('super-admin', 'super-admin', 'System super administrator with access to system settings.', 80, 1),
('admin',       'admin',       'App administrator with full access',                         50, 1),
('manager',     'manager',     'Manager with limited administrative access',                 60, 1),
('up-user',     'up-user',     'Regular user with higher than usual access',                 40, 1),
('user',        'user',        'Regular user with basic access',                             30, 1),
('limit-user',  'limit-user',  'Regular user with limited access',                           20, 1),
('guest',       'guest',       'Guest user with general access',                             10, 1);

-- 9.2 Forms
INSERT OR IGNORE INTO form (form_id, form_name, description) VALUES
('auth.login.view',          'Login page access',     'The /login page'),
('auth.signup.view',         'Signup page access',    'The /signup page'),
('user_profile.view',        'View Profile Page',     'Access to the /profile page'),
('user_profile.edit',        'Edit Profile',          'Ability to edit personal information'),
('account.setting.view',     'View Account Settings', 'Access to /settings/account'),
('account.profile.edit',     'Edit Profile Info',     'Edit personal information'),
('account.password.change',  'Change Password',       'Change account password'),
('account.2fa.manage',       'Manage 2FA',            'Enable/disable two-factor authentication'),
('account.banking.manage',   'Manage Banking',        'Add/edit/remove bank accounts and cards'),
('account.sessions.manage',  'Manage Sessions',       'View and revoke active sessions'),
('account.delete',           'Delete Account',        'Delete own account (danger zone)');

-- 9.3 Activity Types
INSERT OR IGNORE INTO activity_type (activity_type_id, type_name, description) VALUES
(1, 'login',             'User login'),
(2, 'logout',            'User logout'),
(3, 'password_change',   'Password change'),
(4, 'profile_update',    'Profile update'),
(5, 'signup',            'Account signup'),
(6, '2fa_enabled',       'Two-factor authentication enabled'),
(7, '2fa_disabled',      'Two-factor authentication disabled'),
(8, 'subscription_change','Subscription plan changed');

-- 9.4 Address Types
INSERT OR IGNORE INTO address_type (address_type_id, type_name, description) VALUES
(1, 'home',     'Home address'),
(2, 'work',     'Work address'),
(3, 'billing',  'Billing address'),
(4, 'shipping', 'Shipping address');

-- 9.5 Phone Types
INSERT OR IGNORE INTO phone_type (phone_type_id, type_name, description) VALUES
(1, 'mobile', 'Mobile phone'),
(2, 'home',   'Home phone'),
(3, 'work',   'Work phone'),
(4, 'fax',    'Fax number');

-- 9.6 Form Access Grants (level: 0=Closed, 1=Open, >1=Exceptional)
INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
-- Guest
('guest',     'auth.login.view',         1),
('guest',     'auth.signup.view',        1),

-- Limit-user
('limit-user','user_profile.view',       1),
('limit-user','account.setting.view',    1),

-- User
('user',      'user_profile.view',       1),
('user',      'user_profile.edit',       1),
('user',      'account.setting.view',    1),
('user',      'account.profile.edit',    1),
('user',      'account.password.change', 1),
('user',      'account.2fa.manage',      1),

-- Up-user
('up-user',   'user_profile.view',       1),
('up-user',   'user_profile.edit',       1),
('up-user',   'account.setting.view',    1),
('up-user',   'account.profile.edit',    1),
('up-user',   'account.password.change', 1),
('up-user',   'account.2fa.manage',      1),
('up-user',   'account.banking.manage',  1),
('up-user',   'account.sessions.manage', 1),

-- Manager
('manager',   'user_profile.view',       1),
('manager',   'user_profile.edit',       1),
('manager',   'account.setting.view',    1),
('manager',   'account.profile.edit',    1),
('manager',   'account.password.change', 1),
('manager',   'account.2fa.manage',      1),
('manager',   'account.banking.manage',  1),
('manager',   'account.sessions.manage', 1),
('manager',   'account.delete',          1),

-- Admin
('admin',     'user_profile.view',       1),
('admin',     'user_profile.edit',       1),
('admin',     'account.setting.view',    1),
('admin',     'account.profile.edit',    1),
('admin',     'account.password.change', 1),
('admin',     'account.2fa.manage',      1),
('admin',     'account.banking.manage',  1),
('admin',     'account.sessions.manage', 1),
('admin',     'account.delete',          1);

-- =====================================================
-- END OF SCHEMA
-- =====================================================
