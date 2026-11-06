-- =====================================================
-- Database Schema for SQLite - Ramz Project
-- Standardized Structure with Contact-People-User Pattern
-- Version 11.0 (fresh install — level + rank + locks + per-button + crypto)
-- =====================================================
--
-- OVERVIEW
-- --------
-- This file is the fresh-install equivalent of:
--     create_db.v10.0.sql  +  migration_v10_to_v11.sql
--
-- Every statement is idempotent (IF NOT EXISTS / INSERT OR IGNORE).
-- Running on an existing v10 DB adds only the crypto additions.
-- Running on an existing v11 DB is a no-op.
--
-- CHANGELOG v10.0 → v11.0
-- ---------------------
--   * ADDED four crypto tables:
--       - crypto_credential       (encrypted provider API keys)
--       - crypto_symbol_map       (canonical ↔ provider mapping)
--       - crypto_user_preference  (per-user settings per module)
--       - crypto_price_history    (price snapshots for future recorder)
--   * ADDED three indexes for the above.
--   * ADDED six crypto forms (coins view/favorite, charts view/settings,
--     credentials.manage, trade.execute).
--   * ADDED crypto grants (user: read-only; up-user+: extended).
--     crypto.trade.execute intentionally NOT granted yet.
--
-- CHANGELOG v9.0 → v10.0
-- ---------------------
--   * ADDED role: system-admin (rank=70, reserved for future
--     system_settings module, no grants).
--   * ADDED 14 per-button admin_panel forms (users × 3,
--     forms × 4, access × 3, roles × 4).
--   * SUPER-ADMIN grants: full admin_panel access (all 6 section
--     forms + all 14 per-button forms) + base grants (same as
--     admin).
--   * ADMIN/MANAGER grants: users.action.toggle and
--     users.action.reset_password only. No change_role, no CRUD
--     on forms/access/roles.
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
-- 8. CRYPTO
-- =====================================================
-- Crypto tables live in the crypto_market / crypto_providers /
-- crypto_coins / crypto_charts modules, not in db_manager.
-- Repositories for these tables are co-located with the owning module.

-- 8.1 Encrypted provider credentials (per user, per provider, per key type)
CREATE TABLE IF NOT EXISTS crypto_credential (
    credential_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    provider        TEXT NOT NULL,
    key_type        TEXT NOT NULL,
    encrypted_value BLOB NOT NULL,
    nonce           BLOB NOT NULL,
    tag             BLOB NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, provider, key_type)
);

-- 8.2 Canonical → provider symbol mapping
-- `provider_quote` is always a non-NULL string (empty "" when the
-- provider has no quote-currency concept, e.g. an FX rate provider).
-- This avoids the SQLite composite-PK issue where NULL != NULL.
CREATE TABLE IF NOT EXISTS crypto_symbol_map (
    canonical       TEXT NOT NULL,
    provider        TEXT NOT NULL,
    provider_symbol TEXT NOT NULL,
    provider_quote  TEXT,
    PRIMARY KEY (canonical, provider, provider_quote)
);

-- 8.3 Per-user settings, scoped by module namespace
-- Namespace values: "coins", "charts" (extended as new modules need)
CREATE TABLE IF NOT EXISTS crypto_user_preference (
    user_id INTEGER NOT NULL,
    module  TEXT NOT NULL,
    key     TEXT NOT NULL,
    value   TEXT,
    PRIMARY KEY (user_id, module, key),
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

-- 8.4 Price history snapshots (used by future background recorder)
CREATE TABLE IF NOT EXISTS crypto_price_history (
    history_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical   TEXT NOT NULL,
    quote       TEXT NOT NULL,
    price       REAL NOT NULL,
    source      TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Crypto indexes
CREATE INDEX IF NOT EXISTS idx_crypto_credential_user
    ON crypto_credential(user_id, provider);
CREATE INDEX IF NOT EXISTS idx_crypto_symbol_map_provider
    ON crypto_symbol_map(provider, provider_symbol);
CREATE INDEX IF NOT EXISTS idx_crypto_price_history_lookup
    ON crypto_price_history(canonical, quote, recorded_at);

-- =====================================================
-- 9. INDEXES (non-crypto)
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
-- 10. DEFAULT DATA
-- =====================================================

-- 10.1 Roles (with rank for hierarchy)
INSERT OR IGNORE INTO role (role_id, role_name, description, rank, enabled) VALUES
('super-admin',  'super-admin',  'System super administrator with full access.',             80, 1),
('system-admin', 'system-admin', 'Reserved for the future system_settings module.',          70, 1),
('manager',      'manager',      'Manager with limited administrative access',                60, 1),
('admin',        'admin',        'App administrator with full access',                        50, 1),
('up-user',      'up-user',      'Regular user with higher than usual access',                40, 1),
('user',         'user',         'Regular user with basic access',                            30, 1),
('limit-user',   'limit-user',   'Regular user with limited access',                          20, 1),
('guest',        'guest',        'Guest user with general access',                            10, 1);

-- 10.2 Forms
INSERT OR IGNORE INTO form (form_id, form_name, description) VALUES
-- Base auth/account forms
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
('account.delete',           'Delete Account',        'Delete own account (danger zone)'),

-- User panel section
('user_panel.view',          'User Panel Access',     'Access to /panel'),

-- Admin panel — section access
('admin_panel.view',             'Admin Panel Access',   'Access to /settings/admin'),
('admin_panel.users.manage',     'Manage Users',         'Access the Users section'),
('admin_panel.users.view_all',   'View All Users',       'See users with equal or higher role rank'),
('admin_panel.forms.manage',     'Manage Forms',         'Access the Forms section'),
('admin_panel.access.manage',    'Manage Access Grants', 'Access the Access Grants section'),
('admin_panel.roles.view',       'View Roles',           'Access the Roles section'),

-- Admin panel — per-button: Users
('admin_panel.users.action.change_role',    'Change User Role',    'Change another user''s role'),
('admin_panel.users.action.toggle',         'Toggle User Status',  'Enable or disable another user'),
('admin_panel.users.action.reset_password', 'Reset User Password', 'Reset another user''s password'),

-- Admin panel — per-button: Forms
('admin_panel.forms.action.create',  'Create Form',  'Create new forms'),
('admin_panel.forms.action.edit',    'Edit Form',    'Edit existing forms'),
('admin_panel.forms.action.delete',  'Delete Form',  'Delete forms'),
('admin_panel.forms.action.lock',    'Lock Form',    'Toggle form lock (freeze grants)'),

-- Admin panel — per-button: Access Grants
('admin_panel.access.action.create', 'Create Grant', 'Create new access grants'),
('admin_panel.access.action.edit',   'Edit Grant',   'Edit grant levels'),
('admin_panel.access.action.delete', 'Delete Grant', 'Delete access grants'),

-- Admin panel — per-button: Roles
('admin_panel.roles.action.create',  'Create Role',  'Create new roles'),
('admin_panel.roles.action.edit',    'Edit Role',    'Edit existing roles'),
('admin_panel.roles.action.delete',  'Delete Role',  'Delete roles'),
('admin_panel.roles.action.lock',    'Lock Role',    'Toggle role lock (freeze grants)'),

-- Crypto
('crypto.coins.view',          'View Coins Page',              'Access /panel/crypto/coins'),
('crypto.coins.favorite',      'Manage Coin Favorites',        'Toggle favorites and coin display settings'),
('crypto.charts.view',         'View Charts Page',             'Access /panel/crypto/charts'),
('crypto.charts.settings',     'Manage Chart Settings',        'Chart preferences (interval, theme)'),
('crypto.credentials.manage',  'Manage Provider Credentials',  'Store and test provider API keys'),
('crypto.trade.execute',       'Execute Trade',                'Reserved for future trading module');

-- 10.3 Activity Types
INSERT OR IGNORE INTO activity_type (activity_type_id, type_name, description) VALUES
(1, 'login',             'User login'),
(2, 'logout',            'User logout'),
(3, 'password_change',   'Password change'),
(4, 'profile_update',    'Profile update'),
(5, 'signup',            'Account signup'),
(6, '2fa_enabled',       'Two-factor authentication enabled'),
(7, '2fa_disabled',      'Two-factor authentication disabled'),
(8, 'subscription_change','Subscription plan changed');

-- 10.4 Address Types
INSERT OR IGNORE INTO address_type (address_type_id, type_name, description) VALUES
(1, 'home',     'Home address'),
(2, 'work',     'Work address'),
(3, 'billing',  'Billing address'),
(4, 'shipping', 'Shipping address');

-- 10.5 Phone Types
INSERT OR IGNORE INTO phone_type (phone_type_id, type_name, description) VALUES
(1, 'mobile', 'Mobile phone'),
(2, 'home',   'Home phone'),
(3, 'work',   'Work phone'),
(4, 'fax',    'Fax number');

-- 10.6 Form Access Grants (level: 0=Closed, 1=Open, >1=Exceptional)
INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
-- Guest (auth pages only)
('guest',       'auth.login.view',          1),
('guest',       'auth.signup.view',         1),

-- Limit-user (view own account, no edits)
('limit-user',  'user_profile.view',        1),
('limit-user',  'account.setting.view',     1),
('limit-user',  'user_panel.view',          1),

-- User (base self-service)
('user',        'user_profile.view',        1),
('user',        'user_profile.edit',        1),
('user',        'account.setting.view',     1),
('user',        'account.profile.edit',     1),
('user',        'account.password.change',  1),
('user',        'account.2fa.manage',       1),
('user',        'user_panel.view',          1),

-- Up-user (adds banking + sessions)
('up-user',     'user_profile.view',        1),
('up-user',     'user_profile.edit',        1),
('up-user',     'account.setting.view',     1),
('up-user',     'account.profile.edit',     1),
('up-user',     'account.password.change',  1),
('up-user',     'account.2fa.manage',       1),
('up-user',     'account.banking.manage',   1),
('up-user',     'account.sessions.manage',  1),
('up-user',     'user_panel.view',          1),

-- Manager (full base + admin_panel view + users.toggle/reset only)
('manager',     'user_profile.view',        1),
('manager',     'user_profile.edit',        1),
('manager',     'account.setting.view',     1),
('manager',     'account.profile.edit',     1),
('manager',     'account.password.change',  1),
('manager',     'account.2fa.manage',       1),
('manager',     'account.banking.manage',   1),
('manager',     'account.sessions.manage',  1),
('manager',     'account.delete',           1),
('manager',     'user_panel.view',          1),
('manager',     'admin_panel.view',             1),
('manager',     'admin_panel.users.manage',     1),
('manager',     'admin_panel.forms.manage',     1),
('manager',     'admin_panel.access.manage',    1),
('manager',     'admin_panel.roles.view',       1),
('manager',     'admin_panel.users.action.toggle',         1),
('manager',     'admin_panel.users.action.reset_password', 1),

-- Admin (full base + admin_panel view_all + users.toggle/reset only)
('admin',       'user_profile.view',        1),
('admin',       'user_profile.edit',        1),
('admin',       'account.setting.view',     1),
('admin',       'account.profile.edit',     1),
('admin',       'account.password.change',  1),
('admin',       'account.2fa.manage',       1),
('admin',       'account.banking.manage',   1),
('admin',       'account.sessions.manage',  1),
('admin',       'account.delete',           1),
('admin',       'user_panel.view',          1),
('admin',       'admin_panel.view',             1),
('admin',       'admin_panel.users.manage',     1),
('admin',       'admin_panel.users.view_all',   1),
('admin',       'admin_panel.forms.manage',     1),
('admin',       'admin_panel.access.manage',    1),
('admin',       'admin_panel.roles.view',       1),
('admin',       'admin_panel.users.action.toggle',         1),
('admin',       'admin_panel.users.action.reset_password', 1),

-- Super-admin (admin-equivalent base + full admin_panel + all 14 per-buttons)
('super-admin', 'user_profile.view',        1),
('super-admin', 'user_profile.edit',        1),
('super-admin', 'account.setting.view',     1),
('super-admin', 'account.profile.edit',     1),
('super-admin', 'account.password.change',  1),
('super-admin', 'account.2fa.manage',       1),
('super-admin', 'account.banking.manage',   1),
('super-admin', 'account.sessions.manage',  1),
('super-admin', 'account.delete',           1),
('super-admin', 'user_panel.view',          1),
('super-admin', 'admin_panel.view',             1),
('super-admin', 'admin_panel.users.manage',     1),
('super-admin', 'admin_panel.users.view_all',   1),
('super-admin', 'admin_panel.forms.manage',     1),
('super-admin', 'admin_panel.access.manage',    1),
('super-admin', 'admin_panel.roles.view',       1),
('super-admin', 'admin_panel.users.action.change_role',    1),
('super-admin', 'admin_panel.users.action.toggle',         1),
('super-admin', 'admin_panel.users.action.reset_password', 1),
('super-admin', 'admin_panel.forms.action.create',         1),
('super-admin', 'admin_panel.forms.action.edit',           1),
('super-admin', 'admin_panel.forms.action.delete',         1),
('super-admin', 'admin_panel.forms.action.lock',           1),
('super-admin', 'admin_panel.access.action.create',        1),
('super-admin', 'admin_panel.access.action.edit',          1),
('super-admin', 'admin_panel.access.action.delete',        1),
('super-admin', 'admin_panel.roles.action.create',         1),
('super-admin', 'admin_panel.roles.action.edit',           1),
('super-admin', 'admin_panel.roles.action.delete',         1),
('super-admin', 'admin_panel.roles.action.lock',           1);

-- system-admin: intentionally no grants (reserved role)

-- 10.7 Crypto Grants
-- Design:
--   • user: read-only (coins + charts).
--   • up-user and above: + favorites, chart settings, credentials.
--   • crypto.trade.execute: intentionally NOT granted yet
--     (will be granted when crypto_trading module lands).
INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
-- user: read-only
('user',        'crypto.coins.view',          1),
('user',        'crypto.charts.view',         1),

-- up-user
('up-user',     'crypto.coins.view',          1),
('up-user',     'crypto.coins.favorite',      1),
('up-user',     'crypto.charts.view',         1),
('up-user',     'crypto.charts.settings',     1),
('up-user',     'crypto.credentials.manage',  1),

-- manager
('manager',     'crypto.coins.view',          1),
('manager',     'crypto.coins.favorite',      1),
('manager',     'crypto.charts.view',         1),
('manager',     'crypto.charts.settings',     1),
('manager',     'crypto.credentials.manage',  1),

-- admin
('admin',       'crypto.coins.view',          1),
('admin',       'crypto.coins.favorite',      1),
('admin',       'crypto.charts.view',         1),
('admin',       'crypto.charts.settings',     1),
('admin',       'crypto.credentials.manage',  1),

-- super-admin
('super-admin', 'crypto.coins.view',          1),
('super-admin', 'crypto.coins.favorite',      1),
('super-admin', 'crypto.charts.view',         1),
('super-admin', 'crypto.charts.settings',     1),
('super-admin', 'crypto.credentials.manage',  1);

-- =====================================================
-- END OF SCHEMA
-- =====================================================

-- VERIFY (after running):
--   SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'crypto_%';
--   -- expect: 4
--
--   SELECT COUNT(*) FROM form WHERE form_id LIKE 'crypto.%';
--   -- expect: 6
--
--   SELECT COUNT(*) FROM form_access WHERE form_id LIKE 'crypto.%';
--   -- expect: 22
