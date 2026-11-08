"""
credential_repository — CRUD for the `crypto_credential` table.

The table stores ENCRYPTED API keys (one row per
user × provider × key_type). Encryption and decryption are NOT
performed here; this repository only reads and writes raw BLOBs.
The decryption boundary lives in `services.CredentialService`
(TASK 78.3).

Schema recap (from migration v10→v11)
-------------------------------------
    crypto_credential(
        credential_id   INTEGER PK AUTOINCREMENT,
        user_id         INTEGER NOT NULL,   → user(user_id)
        provider        TEXT NOT NULL,      e.g. "nobitex"
        key_type        TEXT NOT NULL,      e.g. "api_key", "api_secret"
        encrypted_value BLOB NOT NULL,      ciphertext from AES-256-GCM
        nonce           BLOB NOT NULL,      GCM nonce (12 bytes)
        tag             BLOB NOT NULL,      GCM auth tag (16 bytes)
        created_at, updated_at
    )
    UNIQUE(user_id, provider, key_type)

Security contract
-----------------
    • `encrypted_value`, `nonce`, `tag` are always opaque bytes.
      The repository never sees or produces plaintext.
    • Rows are upserted, not inserted blindly, so `credential_id`
      is preserved across updates (audit trail).
    • `updated_at` is set explicitly by this repository on every
      update. The schema has no ON UPDATE trigger, so leaving it to
      the DB would not reflect when the key was actually changed.

BLOB normalization
------------------
Different DB drivers return BLOB columns as different Python types:
    • aiosqlite → bytes
    • asyncpg   → memoryview
    • aiomysql  → bytes

`_normalize_blob` coerces to bytes so callers always receive a
consistent type regardless of backend. Called on every returned row.

DB portability
--------------
All queries use the framework's high-level `find_one` / `find_many`
/ `insert` / `update` / `delete` methods (dict-based, no SQL string
literals). This keeps the repository portable across SQLite /
PostgreSQL / MySQL without change.
"""
from datetime import datetime
from typing import Optional


class CredentialRepository:
    """CRUD for crypto_credential (encrypted at rest, opaque to repo)."""

    TABLE = "crypto_credential"

    # Columns that hold raw bytes (encrypted content). Coerced to
    # `bytes` in _normalize_row for backend portability.
    _BLOB_FIELDS = ("encrypted_value", "nonce", "tag")

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger

    def _conn(self):
        return self._db.connection()

    def _log(self, message, level="INFO"):
        if self._logger:
            try:
                self._logger.log(
                    message, level=level, tag="crypto_providers"
                )
            except Exception:
                pass

    @staticmethod
    def _normalize_row(row: Optional[dict]) -> Optional[dict]:
        """
        Return a copy of `row` with BLOB columns coerced to `bytes`.

        No-op on None. Unknown fields are preserved untouched.
        """
        if row is None:
            return None
        normalized = dict(row)
        for field in CredentialRepository._BLOB_FIELDS:
            value = normalized.get(field)
            if value is not None and not isinstance(value, bytes):
                try:
                    normalized[field] = bytes(value)
                except Exception:
                    # Leave as-is if coercion fails; caller will fail
                    # loudly on decrypt (which is the right place).
                    pass
        return normalized

    # ----------------------------------------------------------
    # Reads
    # ----------------------------------------------------------
    async def get(
        self, user_id: int, provider: str, key_type: str
    ) -> Optional[dict]:
        """
        Return the credential row for (user_id, provider, key_type),
        or None.

        The row contains `encrypted_value`, `nonce`, `tag` as bytes.
        It does NOT contain plaintext — caller must decrypt.
        """
        if not user_id or not provider or not key_type:
            return None
        try:
            row = await self._conn().find_one(
                self.TABLE,
                where={
                    "user_id":  int(user_id),
                    "provider": provider,
                    "key_type": key_type,
                },
            )
            return self._normalize_row(row)
        except Exception as exc:
            self._log(f"get failed: {exc}", level="ERROR")
            return None

    async def list_by_user_and_provider(
        self, user_id: int, provider: str
    ) -> list[dict]:
        """
        Return all credential rows for a given provider.

        Example: for Nobitex, this typically returns two rows
        (api_key, api_secret), each with encrypted bytes.
        """
        if not user_id or not provider:
            return []
        try:
            rows = await self._conn().find_many(
                self.TABLE,
                where={
                    "user_id":  int(user_id),
                    "provider": provider,
                },
            )
            return [self._normalize_row(r) for r in (rows or [])]
        except Exception as exc:
            self._log(
                f"list_by_user_and_provider failed: {exc}",
                level="ERROR",
            )
            return []

    async def list_by_user(self, user_id: int) -> list[dict]:
        """
        Return all credential rows for a user (across all providers).

        Used by the settings UI to show which providers are configured.
        """
        if not user_id:
            return []
        try:
            rows = await self._conn().find_many(
                self.TABLE, where={"user_id": int(user_id)}
            )
            return [self._normalize_row(r) for r in (rows or [])]
        except Exception as exc:
            self._log(f"list_by_user failed: {exc}", level="ERROR")
            return []

    async def list_providers(self, user_id: int) -> list[str]:
        """
        Return the sorted list of distinct provider names a user has
        configured credentials for.

        Uses find_many (DB-portable) + Python-side dedup. For a user
        with a small number of credentials (typical: 2-5), loading the
        full rows is negligible. If this ever becomes hot, replace
        with a raw `SELECT DISTINCT provider` in a driver-specific
        optimization; the public signature will not change.
        """
        rows = await self.list_by_user(user_id)
        seen = set()
        providers = []
        for row in rows:
            p = row.get("provider")
            if p and p not in seen:
                seen.add(p)
                providers.append(p)
        providers.sort()
        return providers

    async def has_credentials(
        self, user_id: int, provider: str
    ) -> bool:
        """
        True if at least one key_type is stored for (user_id, provider).
        """
        rows = await self.list_by_user_and_provider(user_id, provider)
        return bool(rows)

    # ----------------------------------------------------------
    # Writes
    # ----------------------------------------------------------
    async def upsert(
        self,
        user_id: int,
        provider: str,
        key_type: str,
        encrypted_value: bytes,
        nonce: bytes,
        tag: bytes,
    ) -> bool:
        """
        Insert or update one credential row.

        Preserves `credential_id` on update (find-then-update pattern
        rather than SQLite's INSERT OR REPLACE, which would rotate
        the id). Sets `updated_at` explicitly.

        Returns True on success.
        """
        if (
            not user_id
            or not provider
            or not key_type
            or encrypted_value is None
            or nonce is None
            or tag is None
        ):
            return False

        where = {
            "user_id":  int(user_id),
            "provider": provider,
            "key_type": key_type,
        }
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        try:
            existing = await self._conn().find_one(
                self.TABLE, where=where
            )
            if existing:
                result = await self._conn().update(
                    self.TABLE,
                    data={
                        "encrypted_value": encrypted_value,
                        "nonce":           nonce,
                        "tag":             tag,
                        "updated_at":      now_str,
                    },
                    where=where,
                )
            else:
                result = await self._conn().insert(
                    self.TABLE,
                    data={
                        "user_id":         int(user_id),
                        "provider":        provider,
                        "key_type":        key_type,
                        "encrypted_value": encrypted_value,
                        "nonce":           nonce,
                        "tag":             tag,
                    },
                )
            return bool(getattr(result, "success", False))
        except Exception as exc:
            self._log(f"upsert failed: {exc}", level="ERROR")
            return False

    async def delete(
        self, user_id: int, provider: str, key_type: str
    ) -> bool:
        """Delete one credential row. Returns True on success (or if
        it did not exist — idempotent)."""
        if not user_id or not provider or not key_type:
            return False
        try:
            result = await self._conn().delete(
                self.TABLE,
                where={
                    "user_id":  int(user_id),
                    "provider": provider,
                    "key_type": key_type,
                },
            )
            return bool(getattr(result, "success", False))
        except Exception as exc:
            self._log(f"delete failed: {exc}", level="ERROR")
            return False

    async def delete_provider(
        self, user_id: int, provider: str
    ) -> bool:
        """
        Delete ALL credential rows for a user × provider.

        Idempotent: returns True even if no rows existed. This mirrors
        common REST DELETE semantics — the caller typically does not
        care whether the row was already gone.
        """
        if not user_id or not provider:
            return False
        try:
            result = await self._conn().delete(
                self.TABLE,
                where={
                    "user_id":  int(user_id),
                    "provider": provider,
                },
            )
            return bool(getattr(result, "success", False))
        except Exception as exc:
            self._log(f"delete_provider failed: {exc}", level="ERROR")
            return False

    async def delete_all(self, user_id: int) -> bool:
        """
        Delete ALL credentials for a user (across all providers).

        Used during account deletion / cleanup.
        Idempotent.
        """
        if not user_id:
            return False
        try:
            result = await self._conn().delete(
                self.TABLE,
                where={"user_id": int(user_id)},
            )
            return bool(getattr(result, "success", False))
        except Exception as exc:
            self._log(f"delete_all failed: {exc}", level="ERROR")
            return False

    # ----------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------
    def __repr__(self) -> str:
        return "CredentialRepository()"


__all__ = ["CredentialRepository"]
