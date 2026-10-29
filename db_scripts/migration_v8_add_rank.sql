-- =====================================================
-- Migration: v7.0 → v8.0 (Ramz Project)
-- Add role.rank (numeric hierarchy)
-- =====================================================
--
-- WHAT IT DOES
-- ------------
--   1. Adds `rank INTEGER NOT NULL DEFAULT 0` to `role`
--   2. Sets rank for known roles:
--        super-admin=80, system-admin=70 (if exists),
--        manager=60, admin=50, up-user=40, user=30,
--        limit-user=20, guest=10
--
-- BEFORE RUNNING
-- --------------
--   • BACK UP your database:
--       cp data/rmz_data.db data/rmz_data.db.bak-v8
--   • Stop the server.
--
-- HOW TO RUN
-- ----------
--   sqlite3 data/rmz_data.db < db_scripts/migration_v8_add_rank.sql
--
-- NOTE: This migration is NOT idempotent. Run exactly once.
-- If re-run, it will fail on "duplicate column name: rank".
-- =====================================================

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

ALTER TABLE role ADD COLUMN rank INTEGER NOT NULL DEFAULT 0;

UPDATE role SET rank = 80 WHERE role_id = 'super-admin';
UPDATE role SET rank = 70 WHERE role_id = 'system-admin';
UPDATE role SET rank = 60 WHERE role_id = 'manager';
UPDATE role SET rank = 50 WHERE role_id = 'admin';
UPDATE role SET rank = 40 WHERE role_id = 'up-user';
UPDATE role SET rank = 30 WHERE role_id = 'user';
UPDATE role SET rank = 20 WHERE role_id = 'limit-user';
UPDATE role SET rank = 10 WHERE role_id = 'guest';

COMMIT;
PRAGMA foreign_keys = ON;

-- =====================================================
-- DONE — verify with:
--   SELECT role_id, rank FROM role ORDER BY rank DESC;
-- =====================================================
