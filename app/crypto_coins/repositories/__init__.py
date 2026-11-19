"""
repositories — database access for crypto_coins.

Contains:
    user_preference_repository.py — crypto_user_preference CRUD
                                    (favorites, display prefs)

Repositories live inside their owning module (not in db_manager).
They receive the app's db service via constructor and use
`db_service.connection()` to obtain a connection.
"""
from .user_preference_repository import (
    UserPreferenceRepository,
    KEY_FAVORITES,
    KEY_DISPLAY_CURRENCY,
    KEY_ROWS_PER_PAGE,
    DEFAULT_DISPLAY_CURRENCY,
    DEFAULT_ROWS_PER_PAGE,
    VALID_DISPLAY_CURRENCIES,
    MIN_ROWS_PER_PAGE,
    MAX_ROWS_PER_PAGE,
)

__all__ = [
    "UserPreferenceRepository",
    "KEY_FAVORITES",
    "KEY_DISPLAY_CURRENCY",
    "KEY_ROWS_PER_PAGE",
    "DEFAULT_DISPLAY_CURRENCY",
    "DEFAULT_ROWS_PER_PAGE",
    "VALID_DISPLAY_CURRENCIES",
    "MIN_ROWS_PER_PAGE",
    "MAX_ROWS_PER_PAGE",
]
