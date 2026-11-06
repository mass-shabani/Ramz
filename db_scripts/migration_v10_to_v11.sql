-- =====================================================
-- Migration: v10.0 → v11.0 (Ramz Project)
-- Add crypto tables + forms + grants
-- =====================================================
--
-- WHAT IT DOES
-- ------------
--   1. Creates four crypto tables:
--        • crypto_credential       — encrypted API keys per user/provider
--        • crypto_symbol_map       — canonical ↔ provider symbol mapping
--        • crypto_user_preference  — per-user settings (favorites, chart prefs)
--        • crypto_price_history    — price snapshots (used by future recorder)
--   2. Adds indexes for the above.
--   3. Inserts six crypto forms.
--   4. Inserts default grants for the six forms.
--
-- IDEMPOTENT
-- ----------
-- This script uses `CREATE TABLE IF NOT EXISTS`,
-- `CREATE INDEX IF NOT EXISTS`, and `INSERT OR IGNORE`.
-- Safe to run multiple times; no-op on already-migrated DBs.
--
-- WHAT IT DOES NOT DO
-- -------------------
--   • Does not touch any existing row in user, people, role,
--     form_access (pre-existing), user_activity_log, etc.
--   • Does not drop or alter any existing table/column.
--   • Does not delete any data.
--
-- BEFORE RUNNING
-- --------------
--   • BACK UP the database (user action):
--       cp data/rmz_data.db data/rmz_data.db.bak-v11-YYYYMMDD
--   • Stop the server.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/migration_v10_to_v11.sql
--
-- =====================================================

PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

-- =====================================================
-- 1. CRYPTO TABLES
-- =====================================================

-- 1.1 Encrypted provider credentials (per user, per provider, per key type)
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

-- 1.2 Canonical → provider symbol mapping
CREATE TABLE IF NOT EXISTS crypto_symbol_map (
    canonical       TEXT NOT NULL,
    provider        TEXT NOT NULL,
    provider_symbol TEXT NOT NULL,
    provider_quote  TEXT,
    PRIMARY KEY (canonical, provider, provider_quote)
);

-- 1.3 Per-user settings scoped by module namespace
CREATE TABLE IF NOT EXISTS crypto_user_preference (
    user_id INTEGER NOT NULL,
    module  TEXT NOT NULL,
    key     TEXT NOT NULL,
    value   TEXT,
    PRIMARY KEY (user_id, module, key),
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

-- 1.4 Price history snapshots (future: used by background recorder)
CREATE TABLE IF NOT EXISTS crypto_price_history (
    history_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical   TEXT NOT NULL,
    quote       TEXT NOT NULL,
    price       REAL NOT NULL,
    source      TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 2. INDEXES
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_crypto_credential_user
    ON crypto_credential(user_id, provider);

CREATE INDEX IF NOT EXISTS idx_crypto_symbol_map_provider
    ON crypto_symbol_map(provider, provider_symbol);

CREATE INDEX IF NOT EXISTS idx_crypto_price_history_lookup
    ON crypto_price_history(canonical, quote, recorded_at);

-- =====================================================
-- 3. FORMS
-- =====================================================

INSERT OR IGNORE INTO form (form_id, form_name, description) VALUES
('crypto.coins.view',          'View Coins Page',              'Access /panel/crypto/coins'),
('crypto.coins.favorite',      'Manage Coin Favorites',        'Toggle favorites and coin display settings'),
('crypto.charts.view',         'View Charts Page',             'Access /panel/crypto/charts'),
('crypto.charts.settings',     'Manage Chart Settings',        'Chart preferences (interval, theme)'),
('crypto.credentials.manage',  'Manage Provider Credentials',  'Store and test provider API keys'),
('crypto.trade.execute',       'Execute Trade',                'Reserved for future trading module');

-- =====================================================
-- 4. GRANTS
-- =====================================================
-- Design:
--   • All authenticated roles can VIEW coins and charts (read-only data).
--   • up-user and higher can manage favorites, chart settings, credentials.
--   • crypto.trade.execute — no grants yet (reserved).

INSERT OR IGNORE INTO form_access (role_id, form_id, level) VALUES
-- user: read-only
('user',        'crypto.coins.view',          1),
('user',        'crypto.charts.view',         1),

-- up-user: + favorites, chart settings, credentials
('up-user',     'crypto.coins.view',          1),
('up-user',     'crypto.coins.favorite',      1),
('up-user',     'crypto.charts.view',         1),
('up-user',     'crypto.charts.settings',     1),
('up-user',     'crypto.credentials.manage',  1),

-- manager: same as up-user
('manager',     'crypto.coins.view',          1),
('manager',     'crypto.coins.favorite',      1),
('manager',     'crypto.charts.view',         1),
('manager',     'crypto.charts.settings',     1),
('manager',     'crypto.credentials.manage',  1),

-- admin: same as up-user
('admin',       'crypto.coins.view',          1),
('admin',       'crypto.coins.favorite',      1),
('admin',       'crypto.charts.view',         1),
('admin',       'crypto.charts.settings',     1),
('admin',       'crypto.credentials.manage',  1),

-- super-admin: same as up-user
('super-admin', 'crypto.coins.view',          1),
('super-admin', 'crypto.coins.favorite',      1),
('super-admin', 'crypto.charts.view',         1),
('super-admin', 'crypto.charts.settings',     1),
('super-admin', 'crypto.credentials.manage',  1);

-- crypto.trade.execute — intentionally NOT granted yet
-- (will be granted when crypto_trading module lands)

COMMIT;
PRAGMA foreign_keys = OFF;

-- =====================================================
-- DONE — verify with:
--   SELECT form_id, form_name FROM form WHERE form_id LIKE 'crypto.%';
--   -- expect: 6 rows
--
--   SELECT role_id, form_id, level FROM form_access
--   WHERE form_id LIKE 'crypto.%' ORDER BY role_id, form_id;
--   -- expect: 19 rows (user: 2, up-user: 5, manager: 5, admin: 5, super-admin: 5)
-- =====================================================
