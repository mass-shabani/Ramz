"""
services — CredentialService for provider API keys.

Encrypts and decrypts per-user API keys, using `EncryptionAPI` from
`system_encryption` (AES-256-GCM) and a stable master key managed by
`MasterKeyManager`. Delegates raw BLOB storage to
`CredentialRepository`.

Security contract
-----------------
    • Plaintext keys are NEVER logged, NEVER stored in memory beyond
      the duration of a single call, and NEVER returned outside the
      caller's scope.
    • The master key is NEVER logged.
    • On `save_credentials`, every key is encrypt-then-decrypt
      round-tripped in memory BEFORE any DB write. If any round-trip
      fails, nothing is stored — the user can retry with a clear
      error, and the DB does not end up with unreadable ciphertext.

Design notes
------------
    • Empty string values in the input dict are SKIPPED. This matches
      the settings UI contract: leaving a field blank means "do not
      change that key", not "overwrite with empty string". Callers
      that explicitly want to delete a key must use
      `delete_credentials()` (or a future per-key delete method).

    • Partial failures on save are possible: if `api_key` upserts
      successfully but `api_secret` fails, the DB ends up with
      inconsistent state. This is a deliberate trade-off — wrapping
      multiple upserts in a transaction would require the repository
      to expose a connection-scoped transaction API, which
      contradicts the current per-call connection model. In practice
      the failure rate for two sequential SQLite upserts is
      effectively zero, and a retry by the user fixes the state. A
      future version can add transactional saves if needed.

    • `get_credentials` returns a dict of successfully decrypted
      keys. If a single key fails to decrypt (e.g. key was rotated
      manually), it is logged and SKIPPED, and the rest are still
      returned. Consumers should check for the keys they need.
"""
from typing import Optional

# Imported from system_encryption (bundled with massir). The class is
# used only to construct an EncryptedData envelope when decrypting a
# row read from the DB — see `_decrypt_row`.
from massir.modules.system_encryption.core.encryption_api import (
    EncryptedData,
)


# Algorithm identifier used when constructing EncryptedData envelopes
# for decryption. Matches `encryption_api.encrypt`'s algorithm.
_ALGORITHM = "aes-256-gcm"


class CredentialService:
    """
    Encrypted credential storage and retrieval.

    See module docstring for the security contract and design notes.
    """

    def __init__(
        self,
        repository,
        encryption_api,
        key_manager,
        logger=None,
    ):
        self._repo = repository
        self._encryption_api = encryption_api
        self._key_manager = key_manager
        self._logger = logger

    # ==========================================================
    # Save
    # ==========================================================
    async def save_credentials(
        self,
        user_id: int,
        provider: str,
        keys: dict,
    ) -> tuple[bool, Optional[str]]:
        """
        Encrypt and store one or more API keys for a user × provider.

        Args:
            user_id:  Owner user id.
            provider: Provider name (e.g. "nobitex").
            keys:     Dict of {key_type: plaintext_value}. Empty
                      string values are skipped (see module
                      docstring).

        Returns:
            (True, None) on full success.
            (False, code) on failure. Possible codes:
                • "invalid_input"    — keys not a dict, or user/provider
                                       missing
                • "empty_keys"       — no non-empty keys after filtering
                • "key_unavailable"  — master key could not be loaded
                • "encrypt_failed"   — encryption_api raised
                • "verify_failed"    — round-trip check failed
                • "store_failed"     — repository.upsert returned False
        """
        if not user_id or not provider:
            return False, "invalid_input"
        if not isinstance(keys, dict) or not keys:
            return False, "invalid_input"

        # ---- Sanitize input -----------------------------------
        sanitized: dict[str, str] = {}
        for raw_key_type, raw_value in keys.items():
            if not isinstance(raw_key_type, str):
                continue
            key_type = raw_key_type.strip()
            if not key_type:
                continue
            if not isinstance(raw_value, str):
                continue
            if not raw_value.strip():
                # Skip empty — see module docstring.
                continue
            sanitized[key_type] = raw_value

        if not sanitized:
            return False, "empty_keys"

        # ---- Master key ---------------------------------------
        try:
            master_key = self._key_manager.get_key()
        except Exception as exc:
            self._log(
                f"Master key unavailable: {exc}", level="ERROR"
            )
            return False, "key_unavailable"

        # ---- Encrypt + verify round-trip (no DB yet) ----------
        encrypted_data = {}
        for key_type, plaintext in sanitized.items():
            try:
                plaintext_bytes = plaintext.encode("utf-8")
                encrypted = self._encryption_api.encrypt(
                    plaintext_bytes, master_key
                )
                roundtrip = self._encryption_api.decrypt(
                    encrypted, master_key
                )
                if roundtrip != plaintext_bytes:
                    self._log(
                        f"Round-trip mismatch for key_type="
                        f"{key_type!r}",
                        level="ERROR",
                    )
                    return False, "verify_failed"
                encrypted_data[key_type] = encrypted
            except Exception as exc:
                self._log(
                    f"Encryption failed for key_type={key_type!r}: "
                    f"{exc}",
                    level="ERROR",
                )
                return False, "encrypt_failed"

        # ---- Store all ----------------------------------------
        for key_type, encrypted in encrypted_data.items():
            try:
                ok = await self._repo.upsert(
                    user_id=user_id,
                    provider=provider,
                    key_type=key_type,
                    encrypted_value=encrypted.ciphertext,
                    nonce=encrypted.nonce,
                    tag=encrypted.tag,
                )
            except Exception as exc:
                self._log(
                    f"Repository upsert raised for key_type="
                    f"{key_type!r}: {exc}",
                    level="ERROR",
                )
                return False, "store_failed"
            if not ok:
                self._log(
                    f"Repository upsert returned False for "
                    f"key_type={key_type!r}",
                    level="ERROR",
                )
                return False, "store_failed"

        self._log(
            f"Stored {len(encrypted_data)} credential(s) "
            f"for user_id={user_id}, provider={provider!r}"
        )
        return True, None

    # ==========================================================
    # Read
    # ==========================================================
    async def get_credentials(
        self, user_id: int, provider: str
    ) -> Optional[dict]:
        """
        Return a dict of {key_type: plaintext} for the user × provider.

        Returns None if no credentials exist or the master key is
        unavailable. Individual rows that fail to decrypt are logged
        and skipped — the caller receives whatever decrypted
        successfully.
        """
        if not user_id or not provider:
            return None

        rows = await self._repo.list_by_user_and_provider(
            user_id, provider
        )
        if not rows:
            return None

        try:
            master_key = self._key_manager.get_key()
        except Exception as exc:
            self._log(
                f"Master key unavailable: {exc}", level="ERROR"
            )
            return None

        result: dict[str, str] = {}
        for row in rows:
            key_type = row.get("key_type")
            if not key_type:
                continue
            plaintext = self._decrypt_row(row, master_key)
            if plaintext is not None:
                result[key_type] = plaintext

        return result or None

    async def get_credential(
        self, user_id: int, provider: str, key_type: str
    ) -> Optional[str]:
        """
        Return the plaintext of a single key, or None.

        Convenience wrapper over `get_credentials` for the common
        case where the caller needs exactly one key.
        """
        if not user_id or not provider or not key_type:
            return None

        row = await self._repo.get(user_id, provider, key_type)
        if not row:
            return None

        try:
            master_key = self._key_manager.get_key()
        except Exception as exc:
            self._log(
                f"Master key unavailable: {exc}", level="ERROR"
            )
            return None

        return self._decrypt_row(row, master_key)

    # ==========================================================
    # Delete
    # ==========================================================
    async def delete_credentials(
        self, user_id: int, provider: str
    ) -> bool:
        """
        Delete all credentials for the user × provider.

        Idempotent — returns True even if nothing was stored.
        """
        if not user_id or not provider:
            return False
        return await self._repo.delete_provider(user_id, provider)

    # ==========================================================
    # Introspection
    # ==========================================================
    async def list_providers(self, user_id: int) -> list[str]:
        """Return the sorted distinct providers the user has keys for."""
        if not user_id:
            return []
        return await self._repo.list_providers(user_id)

    async def has_credentials(
        self, user_id: int, provider: str
    ) -> bool:
        """True if any key is stored for the user × provider."""
        if not user_id or not provider:
            return False
        return await self._repo.has_credentials(user_id, provider)

    # ==========================================================
    # Internal
    # ==========================================================
    def _decrypt_row(
        self, row: dict, master_key: bytes
    ) -> Optional[str]:
        """
        Decrypt one row. Returns None on any error (logged).

        Constructs an EncryptedData envelope from the row's BLOB
        columns. The repository guarantees those columns are `bytes`
        (it normalizes memoryview from asyncpg).
        """
        key_type = row.get("key_type") or "<unknown>"
        ciphertext = row.get("encrypted_value")
        nonce = row.get("nonce")
        tag = row.get("tag")

        if ciphertext is None or nonce is None or tag is None:
            self._log(
                f"Row for key_type={key_type!r} is missing BLOB "
                f"columns",
                level="WARNING",
            )
            return None

        try:
            envelope = EncryptedData(
                algorithm=_ALGORITHM,
                ciphertext=ciphertext,
                nonce=nonce,
                tag=tag,
            )
            plaintext_bytes = self._encryption_api.decrypt(
                envelope, master_key
            )
            return plaintext_bytes.decode("utf-8")
        except Exception as exc:
            self._log(
                f"Decryption failed for key_type={key_type!r}: {exc}",
                level="WARNING",
            )
            return None

    def _log(self, message: str, level: str = "INFO") -> None:
        if self._logger:
            try:
                self._logger.log(
                    message, level=level, tag="crypto_providers"
                )
            except Exception:
                pass

    def __repr__(self) -> str:
        return "CredentialService()"


__all__ = ["CredentialService"]
