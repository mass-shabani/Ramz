"""
key_manager — master key management for CredentialService.

Purpose
-------
`CredentialService` needs a stable 32-byte AES-256 key to encrypt and
decrypt provider API keys. This manager produces and persists that key
in a file, so encrypted credentials survive restarts.

Design
------
    • Single app-wide master key (not per-user, not per-provider).
      Rationale: server-side credential storage for a small number of
      providers does not benefit from per-user keys — those would need
      to be derived from something (user password, KMS) and complicate
      both login and password-reset flows. A single master key is the
      standard pattern for this scale.

    • File-based storage. Path defaults to `{app_dir}/keys/crypto_credentials.key`
      and is overridable via `core_config.get("crypto_providers.credentials_key_path")`.
      The file contains exactly 32 raw bytes (not base64, not JSON).

    • Auto-created on first startup. A warning is logged with a clear
      instruction to back up the file — losing it makes all stored
      credentials unrecoverable (they would fail to decrypt).

    • Lazy loading. `get_key()` reads the file on first call and
      caches the result. `module.start()` warms up the cache once so
      any I/O error surfaces at startup, not at first credential save.

    • Unix permissions on creation are set to 0o600. On startup, if
      the file is group- or world-readable, a warning is logged. On
      Windows, the permission check is skipped.

Limitations
-----------
    • No key rotation. Rotating the master key requires re-encrypting
      all stored credentials, which is out of scope for phase 2. If
      the key is deleted, all existing ciphertext becomes unreadable.

    • No KMS / HSM integration. A future version could replace this
      manager with a KMS-backed implementation without changing the
      `CredentialService` API — that is the reason the key
      management logic lives in its own file.
"""
import os
import stat
from pathlib import Path
from typing import Optional


DEFAULT_PATH_TEMPLATE = "{app_dir}/keys/crypto_credentials.key"
DEFAULT_KEY_SIZE = 32  # bytes — AES-256


class MasterKeyManager:
    """
    Loads or creates the app's master encryption key.

    See module docstring for the design and limitations.
    """

    def __init__(self, app_dir: str, config=None, logger=None):
        self._app_dir = str(app_dir) if app_dir else ""
        self._config = config
        self._logger = logger
        self._path = self._resolve_path()
        self._key: Optional[bytes] = None

    # ----------------------------------------------------------
    # Public
    # ----------------------------------------------------------
    def get_key(self) -> bytes:
        """
        Return the master key, loading or creating it on first call.

        Raises RuntimeError if the file exists with the wrong size or
        cannot be read/created.
        """
        if self._key is None:
            self._key = self._load_or_create()
        return self._key

    def key_path(self) -> str:
        """Return the absolute path to the key file (for logging)."""
        return str(self._path)

    # ----------------------------------------------------------
    # Internal
    # ----------------------------------------------------------
    def _resolve_path(self) -> Path:
        """
        Resolve the key file path from config, substituting
        `{app_dir}`. Falls back to DEFAULT_PATH_TEMPLATE.
        """
        template = DEFAULT_PATH_TEMPLATE
        if self._config:
            try:
                configured = self._config.get(
                    "crypto_providers.credentials_key_path", None
                )
                if configured:
                    template = configured
            except Exception:
                pass

        expanded = template.replace("{app_dir}", self._app_dir)
        return Path(expanded)

    def _load_or_create(self) -> bytes:
        """Load existing key or create a new one; validate size."""
        if self._path.exists():
            try:
                data = self._path.read_bytes()
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to read master key file {self._path}: {exc}"
                )

            if len(data) != DEFAULT_KEY_SIZE:
                raise RuntimeError(
                    f"Master key file {self._path} has wrong size "
                    f"({len(data)} bytes, expected {DEFAULT_KEY_SIZE}). "
                    f"This is not a valid key; refusing to start."
                )

            self._check_permissions()
            self._log(
                f"Master key loaded from {self._path} "
                f"({len(data)} bytes)"
            )
            return data

        # Create new key
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to create directory for master key "
                f"({self._path.parent}): {exc}"
            )

        key = os.urandom(DEFAULT_KEY_SIZE)
        try:
            self._path.write_bytes(key)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to write master key to {self._path}: {exc}"
            )

        try:
            os.chmod(self._path, 0o600)
        except (OSError, NotImplementedError):
            pass  # Windows or FS without Unix permissions

        self._log(
            f"Master key CREATED at {self._path}. "
            f"BACK UP THIS FILE — losing it makes all stored "
            f"credentials unrecoverable.",
            level="WARNING",
        )
        return key

    def _check_permissions(self) -> None:
        """
        Warn if the key file is group- or world-readable on Unix.

        Skipped on Windows (no Unix permissions).
        """
        if os.name == "nt":
            return
        try:
            st = os.stat(self._path)
            mode = stat.S_IMODE(st.st_mode)
            if mode & 0o077:
                self._log(
                    f"Master key file {self._path} has unsafe "
                    f"permissions (mode={oct(mode)}); "
                    f"recommended: 0o600",
                    level="WARNING",
                )
        except Exception:
            pass

    def _log(self, message: str, level: str = "INFO") -> None:
        if self._logger:
            try:
                self._logger.log(
                    message, level=level, tag="crypto_providers"
                )
            except Exception:
                pass

    def __repr__(self) -> str:
        return f"MasterKeyManager(path={self._path})"


__all__ = ["MasterKeyManager", "DEFAULT_PATH_TEMPLATE", "DEFAULT_KEY_SIZE"]
