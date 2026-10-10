"""
Password security.

Uses bcrypt for hashing. Functions will be implemented in phase 2.
"""


def hash_password(plain: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    To be implemented in phase 2.
    """
    raise NotImplementedError("hash_password — phase 2")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    To be implemented in phase 2.
    """
    raise NotImplementedError("verify_password — phase 2")


def needs_rehash(hashed: str) -> bool:
    """
    Return True if the stored hash uses an outdated cost factor and
    should be re-hashed on next successful login.

    To be implemented in phase 2.
    """
    raise NotImplementedError("needs_rehash — phase 2")
