"""
Password security.

Uses bcrypt for hashing and verification.

Design notes
------------
• bcrypt has a 72-byte limit on the input. Longer passwords are silently
  truncated by the library. This is acceptable for our use case since
  passwords longer than 72 bytes are extremely rare, but callers should
  be aware of this behaviour.

• The cost factor (rounds) is controlled by BCRYPT_ROUNDS. Changing it
  will only affect newly generated hashes. needs_rehash() detects old
  hashes so they can be upgraded on the next successful login.
"""
import bcrypt


# --------------------------------------------------------------
# Configuration
# --------------------------------------------------------------
# Cost factor. Higher = more secure but slower.
# 12 is a good balance for 2026-era hardware.
BCRYPT_ROUNDS = 12

# bcrypt expects passwords to be UTF-8 encoded bytes.
_ENCODING = "utf-8"


# --------------------------------------------------------------
# Public API
# --------------------------------------------------------------
def hash_password(plain: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Parameters
    ----------
    plain : str
        The plaintext password. Must not be empty.

    Returns
    -------
    str
        The bcrypt hash, safe to store in the database.

    Raises
    ------
    ValueError
        If the plaintext password is empty or not a string.
    """
    if not isinstance(plain, str) or not plain:
        raise ValueError("Password must be a non-empty string")

    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain.encode(_ENCODING), salt)
    return hashed.decode(_ENCODING)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    Always returns a bool — never raises on malformed input. This is
    intentional: callers should treat any failure as "wrong password".

    Parameters
    ----------
    plain : str
        The plaintext password provided by the user.
    hashed : str
        The hash stored in the database.

    Returns
    -------
    bool
        True if the password matches, False otherwise.
    """
    if not isinstance(plain, str) or not plain:
        return False
    if not isinstance(hashed, str) or not hashed:
        return False

    try:
        return bcrypt.checkpw(
            plain.encode(_ENCODING),
            hashed.encode(_ENCODING),
        )
    except (ValueError, TypeError):
        return False


def needs_rehash(hashed: str) -> bool:
    """
    Return True if the stored hash uses an outdated cost factor and
    should be re-hashed on next successful login.

    Parameters
    ----------
    hashed : str
        The hash stored in the database.

    Returns
    -------
    bool
        True if the hash should be regenerated.
    """
    if not isinstance(hashed, str) or not hashed:
        return True

    try:
        # bcrypt hash format: $2b$<cost>$<salt+hash>
        parts = hashed.split("$")
        if len(parts) < 4:
            return True
        cost = int(parts[2])
        return cost < BCRYPT_ROUNDS
    except (ValueError, IndexError):
        return True
