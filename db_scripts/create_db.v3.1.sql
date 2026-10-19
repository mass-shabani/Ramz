-- =====================================================
-- Database Schema for SQLite - Ramz Project
-- Standardized Structure with Contact-People-User Pattern
-- Version 3.1 - Final Version (No Triggers)
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
-- 4. USERS & AUTHENTICATION (with 2FA)
-- =====================================================

CREATE TABLE IF NOT EXISTS user (
    user_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    people_id              INTEGER NOT NULL,
    role_id                INTEGER NOT NULL,
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
    FOREIGN KEY (role_id) REFERENCES role(role_id),
    FOREIGN KEY (subscription_id) REFERENCES subscription(subscription_id),
    FOREIGN KEY (email_id) REFERENCES email(email_id),
    FOREIGN KEY (phone_id) REFERENCES phone(phone_id)
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

-- =====================================================
-- 5. CONTACT INFORMATION (One-to-Many from Contact)
-- =====================================================

CREATE TABLE IF NOT EXISTS phone (
    phone_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id   INTEGER NOT NULL,
    phone_number TEXT NOT NULL,
    phone_type   TEXT DEFAULT 'mobile' CHECK(phone_type IN ('mobile', 'home', 'work', 'fax')),
    is_verified  INTEGER NOT NULL DEFAULT 0 CHECK(is_verified IN (0, 1)),
    enabled      INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contact(contact_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS post_address (
    address_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id     INTEGER NOT NULL,
    address_line1  TEXT NOT NULL,
    address_line2  TEXT,
    city           TEXT,
    state_province TEXT,
    postal_code    TEXT,
    country        TEXT DEFAULT 'Iran',
    address_type   TEXT DEFAULT 'home' CHECK(address_type IN ('home', 'work', 'billing', 'shipping')),
    enabled        INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contact(contact_id) ON DELETE CASCADE
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
    contact_id      INTEGER NOT NULL,
    bank_id         INTEGER NOT NULL,
    account_number  TEXT NOT NULL,
    account_name    TEXT NOT NULL,
    iban            TEXT UNIQUE,
    enabled         INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contact(contact_id) ON DELETE CASCADE,
    FOREIGN KEY (bank_id) REFERENCES bank(bank_id)
);

CREATE TABLE IF NOT EXISTS bank_card (
    bank_card_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_account_id  INTEGER NOT NULL,
    card_number      TEXT NOT NULL UNIQUE,
    card_holder_name TEXT NOT NULL,
    expiry_date      DATE,
    enabled          INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bank_account_id) REFERENCES bank_account(bank_account_id) ON DELETE CASCADE
);

-- =====================================================
-- 7. INDEXES FOR PERFORMANCE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_people_contact_id ON people(contact_id);
CREATE INDEX IF NOT EXISTS idx_people_national_code ON people(national_code);
CREATE INDEX IF NOT EXISTS idx_user_people_id ON user(people_id);
CREATE INDEX IF NOT EXISTS idx_user_username ON user(username);
CREATE INDEX IF NOT EXISTS idx_user_role_id ON user(role_id);
CREATE INDEX IF NOT EXISTS idx_user_subscription_id ON user(subscription_id);
CREATE INDEX IF NOT EXISTS idx_user_email_id ON user(email_id);
CREATE INDEX IF NOT EXISTS idx_user_phone_id ON user(phone_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_type_id ON user_activity_log(activity_type_id);
CREATE INDEX IF NOT EXISTS idx_phone_contact_id ON phone(contact_id);
CREATE INDEX IF NOT EXISTS idx_post_address_contact_id ON post_address(contact_id);
CREATE INDEX IF NOT EXISTS idx_email_contact_id ON email(contact_id);
CREATE INDEX IF NOT EXISTS idx_bank_account_contact_id ON bank_account(contact_id);
CREATE INDEX IF NOT EXISTS idx_bank_card_account_id ON bank_card(bank_account_id);
CREATE INDEX IF NOT EXISTS idx_form_access_role_id ON form_access(role_id);

-- =====================================================
-- 8. DEFAULT DATA (Optional - for initial setup)
-- =====================================================

-- Insert default activity types
INSERT OR IGNORE INTO activity_type (type_name, description) VALUES 
    ('login', 'User login event'),
    ('logout', 'User logout event'),
    ('password_change', 'Password changed'),
    ('profile_update', 'Profile information updated'),
    ('2fa_enabled', 'Two-factor authentication enabled'),
    ('2fa_disabled', 'Two-factor authentication disabled'),
    ('subscription_change', 'Subscription plan changed');

-- Insert default roles
INSERT OR IGNORE INTO role (role_name, description) VALUES 
    ('admin', 'System administrator with full access'),
    ('manager', 'Manager with limited administrative access'),
    ('user', 'Regular user with basic access'),
    ('guest', 'Guest user with minimal access');

-- Insert default subscription plans
INSERT OR IGNORE INTO subscription (subscription_name, description, price, duration_days, features) VALUES 
    ('free', 'Free tier with basic features', 0, NULL, 'Basic features only'),
    ('basic', 'Basic paid plan', 100000, 30, 'Enhanced features, priority support'),
    ('premium', 'Premium plan', 500000, 30, 'All features, 24/7 support, advanced analytics'),
    ('enterprise', 'Enterprise plan', 2000000, 30, 'Custom features, dedicated support, SLA');

-- =====================================================
-- END OF SCHEMA
-- =====================================================