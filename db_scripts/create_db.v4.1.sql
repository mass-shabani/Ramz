-- =====================================================
-- Database Schema for SQLite - Ramz Project
-- Standardized Structure with Contact-People-User Pattern
-- Version 4.1 (Idempotent, FK for lookup tables)
-- =====================================================
--
-- IDEMPOTENCY
-- -----------
-- This script is FULLY IDEMPOTENT. It can be run multiple times
-- against the same database without side effects. It only creates
-- missing tables, indexes, and default data. Existing schema and
-- data are never modified, dropped, or truncated.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < data/create_db.sql
--
-- NOTES ON LOOKUP TABLES
-- ----------------------
-- The `address_type` and `phone_type` tables are now referenced via
-- foreign keys from `post_address.address_type_id` and
-- `phone.phone_type_id`. For existing databases, run
-- data/migration_005_address_phone_fk.sql to convert legacy TEXT
-- columns.
--
-- CHANGELOG v4.0 → v4.1
-- ---------------------
--   * post_address.address_type (TEXT) → address_type_id (INTEGER FK)
--   * phone.phone_type (TEXT) → phone_type_id (INTEGER FK)
--   * new indexes for the FK columns
-- =====================================================

-- Enable foreign key constraints in SQLite
PRAGMA foreign_keys = ON;

-- =====================================================
-- 1. LOOKUP & REFERENCE TABLES
-- =====================================================

CREATE TABLE IF NOT EXISTS role (
    role_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name   TEXT NOT NULL UNIQUE,
    description TEXT,
    enabled     INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS condition_of (
    condition_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_name TEXT NOT NULL UNIQUE,
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
-- 3. PEOPLE TABLE (Personal Information)
-- =====================================================

CREATE TABLE IF NOT EXISTS people (
    people_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id         INTEGER NOT NULL,
    first_name         TEXT,
    last_name          TEXT,
    national_code      TEXT UNIQUE,
    birth_date         TEXT,
    gender             TEXT,
    nationality        TEXT DEFAULT 'Iran',
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contact(contact_id) ON DELETE CASCADE
);

-- =====================================================
-- 4. USER CREDENTIALS & AUDIT
-- =====================================================

CREATE TABLE IF NOT EXISTS user (
    user_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    people_id    INTEGER NOT NULL UNIQUE,
    username     TEXT UNIQUE,
    email        TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role_id      INTEGER,
    enabled      INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (people_id) REFERENCES people(people_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES role(role_id)
);

CREATE TABLE IF NOT EXISTS login_log (
    log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    success    INTEGER NOT NULL CHECK(success IN (0, 1)),
    login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_action_log (
    action_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    action      TEXT NOT NULL,
    entity_type TEXT,
    entity_id   INTEGER,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address  TEXT,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS email_verification (
    verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    token           TEXT NOT NULL UNIQUE,
    expires_at      DATETIME NOT NULL,
    used           INTEGER NOT NULL DEFAULT 0 CHECK(used IN (0, 1)),
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS phone_verification (
    phone_verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_id               INTEGER NOT NULL,
    token                  TEXT NOT NULL UNIQUE,
    expires_at             DATETIME NOT NULL,
    used                   INTEGER NOT NULL DEFAULT 0 CHECK(used IN (0, 1)),
    FOREIGN KEY (phone_id) REFERENCES phone(phone_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_activity_log (
    activity_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    activity_type_id INTEGER NOT NULL,
    ip_address       TEXT,
    user_agent       TEXT,
    action_time      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (activity_type_id) REFERENCES activity_type(activity_type_id)
);

CREATE TABLE IF NOT EXISTS form_access (
    role_id      INTEGER NOT NULL,
    form_id      TEXT NOT NULL,
    condition_id INTEGER NOT NULL,
    PRIMARY KEY (role_id, form_id),
    FOREIGN KEY (role_id) REFERENCES role(role_id),
    FOREIGN KEY (form_id) REFERENCES form(form_id),
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
-- 5. CONTACT INFORMATION (One-to-Many from Contact)
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
-- 6. BANKING INFORMATION
-- =====================================================

CREATE TABLE IF NOT EXISTS bank_account (
    bank_account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_id         INTEGER NOT NULL,
    people_id       INTEGER NOT NULL,
    account_number  TEXT NOT NULL,
    account_name    TEXT NOT NULL,
    iban            TEXT,
    enabled         INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bank_id) REFERENCES bank(bank_id),
    FOREIGN KEY (people_id) REFERENCES people(people_id) ON DELETE CASCADE,
    UNIQUE(bank_id, account_number)
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
-- 7. INDEXES
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_contact_enabled ON contact(enabled);
CREATE INDEX IF NOT EXISTS idx_people_national_code ON people(national_code);
CREATE INDEX IF NOT EXISTS idx_user_email ON user(email);
CREATE INDEX IF NOT EXISTS idx_user_people_id ON user(people_id);
CREATE INDEX IF NOT EXISTS idx_user_role_id ON user(role_id);
CREATE INDEX IF NOT EXISTS idx_user_enabled ON user(enabled);
CREATE INDEX IF NOT EXISTS idx_login_log_user_id ON login_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_action_log_user_id ON user_action_log(user_id);
CREATE INDEX IF NOT EXISTS idx_email_verification_token ON email_verification(token);
CREATE INDEX IF NOT EXISTS idx_phone_verification_token ON phone_verification(token);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_user_id ON user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_session_user_id ON user_session(user_id);
CREATE INDEX IF NOT EXISTS idx_user_session_expires ON user_session(expires_at);
CREATE INDEX IF NOT EXISTS idx_phone_contact_id ON phone(contact_id);
CREATE INDEX IF NOT EXISTS idx_phone_type_id ON phone(phone_type_id);
CREATE INDEX IF NOT EXISTS idx_post_address_contact_id ON post_address(contact_id);
CREATE INDEX IF NOT EXISTS idx_post_address_type_id ON post_address(address_type_id);
CREATE INDEX IF NOT EXISTS idx_email_contact_id ON email(contact_id);
CREATE INDEX IF NOT EXISTS idx_bank_account_people_id ON bank_account(people_id);
CREATE INDEX IF NOT EXISTS idx_bank_account_bank_id ON bank_account(bank_id);
CREATE INDEX IF NOT EXISTS idx_bank_card_bank_account_id ON bank_card(bank_account_id);

-- =====================================================
-- 8. DEFAULT DATA
-- =====================================================

INSERT OR IGNORE INTO role (role_id, role_name, description) VALUES
(1, 'admin', 'System administrator'),
(2, 'user', 'Regular user');

INSERT OR IGNORE INTO condition_of (condition_id, condition_name, description) VALUES
(1, 'always', 'Always allowed'),
(2, 'signed_in', 'User must be signed in'),
(3, 'admin_only', 'User must be admin');

INSERT OR IGNORE INTO form (form_id, form_name) VALUES
('personal', 'Personal Information'),
('contact', 'Contact Information'),
('auth', 'Authentication'),
('banking', 'Banking Information');

INSERT OR IGNORE INTO activity_type (activity_type_id, type_name, description) VALUES
(1, 'login', 'User login'),
(2, 'logout', 'User logout'),
(3, 'password_change', 'Password change'),
(4, 'profile_update', 'Profile update'),
(5, 'signup', 'Account signup');

INSERT OR IGNORE INTO address_type (address_type_id, type_name, description) VALUES
(1, 'home', 'Home address'),
(2, 'work', 'Work address'),
(3, 'billing', 'Billing address'),
(4, 'shipping', 'Shipping address');

INSERT OR IGNORE INTO phone_type (phone_type_id, type_name, description) VALUES
(1, 'mobile', 'Mobile phone'),
(2, 'home', 'Home phone'),
(3, 'work', 'Work phone'),
(4, 'fax', 'Fax number');

-- End of schema
