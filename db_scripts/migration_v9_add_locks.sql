-- =====================================================
-- Migration: v8.0 → v9.0 (Ramz Project)
-- Drop form.enabled, add form.lock and role.lock
-- =====================================================
--
-- WHAT IT DOES
-- ------------
--   1. form:   DROP COLUMN enabled  (unused; replaced by form_access.level)
--              ADD COLUMN lock INTEGER NOT NULL DEFAULT 0
--   2. role:   ADD COLUMN lock INTEGER NOT NULL DEFAULT 0
--              (role.enabled is KEPT — used to eject users on login)
--
-- SEMANTICS
-- ---------
--   form.lock = 1  → form cannot be edited/deleted, and no grant
--                    may be created/updated/deleted for it
--   role.lock = 1  → no grant may be created/updated/deleted for it
--   role.enabled = 0 → all users with this role are treated as
--                      disabled (session ejected on next request,
--                      login rejected)
--
-- BEFORE RUNNING
-- --------------
--   • BACK UP your database
--   • Stop the server
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/migration_v9_add_locks.sql
--
-- NOTE: This migration is NOT idempotent. Run exactly once.
-- =====================================================

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- 1. form: drop enabled, add lock
--    SQLite doesn't support DROP COLUMN before 3.35 in all cases,
--    so we rebuild the table.
CREATE TABLE form_new (
    form_id     TEXT PRIMARY KEY,
    form_name   TEXT NOT NULL UNIQUE,
    description TEXT,
    lock        INTEGER NOT NULL DEFAULT 0 CHECK(lock IN (0, 1))
);

INSERT INTO form_new (form_id, form_name, description, lock)
SELECT form_id, form_name, description, 0
FROM form;

DROP TABLE form;
ALTER TABLE form_new RENAME TO form;

-- 2. role: add lock
ALTER TABLE role ADD COLUMN lock INTEGER NOT NULL DEFAULT 0;

COMMIT;
PRAGMA foreign_keys = ON;

-- =====================================================
-- DONE — verify with:
--   SELECT form_id, lock FROM form LIMIT 5;
--   SELECT role_id, enabled, lock FROM role ORDER BY rank DESC;
-- =====================================================
