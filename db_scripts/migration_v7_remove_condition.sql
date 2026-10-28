-- =====================================================
-- Migration: v6.0 → v7.0 (Ramz Project)
-- Remove condition_of, add level to form_access
-- =====================================================
--
-- WHAT IT DOES
-- ------------
--   1. Adds `level` column to form_access
--   2. Populates level from old condition_id:
--        Closed       → 0
--        All other    → 1
--   3. Drops condition_id column (rebuilds table)
--   4. Drops condition_of table
--
-- BEFORE RUNNING
-- --------------
--   • BACK UP your database:
--       cp data/rmz_data.db data/rmz_data.db.bak
--   • Ensure the app is stopped.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/migration_v7_remove_condition.sql
--
-- NOTE: This script is NOT idempotent — run it exactly once.
-- If re-run, it will fail on "no such column: condition_id".
-- =====================================================

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- 1. New form_access table with level
CREATE TABLE form_access_new (
    role_id TEXT NOT NULL,
    form_id TEXT NOT NULL,
    level   INTEGER NOT NULL DEFAULT 1 CHECK(level >= 0),
    PRIMARY KEY (role_id, form_id),
    FOREIGN KEY (role_id) REFERENCES role(role_id),
    FOREIGN KEY (form_id) REFERENCES form(form_id)
);

-- 2. Copy data, translating conditions to levels
INSERT INTO form_access_new (role_id, form_id, level)
SELECT
    role_id,
    form_id,
    CASE
        WHEN condition_id = 'Closed' THEN 0
        ELSE 1
    END
FROM form_access;

-- 3. Swap
DROP TABLE form_access;
ALTER TABLE form_access_new RENAME TO form_access;

-- 4. Drop condition_of
DROP TABLE IF EXISTS condition_of;

-- 5. Recreate indexes
CREATE INDEX IF NOT EXISTS idx_form_access_role_id ON form_access(role_id);

COMMIT;
PRAGMA foreign_keys = ON;

-- =====================================================
-- DONE
-- =====================================================
