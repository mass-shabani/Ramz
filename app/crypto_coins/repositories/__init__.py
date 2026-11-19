"""
repositories — database access for crypto_coins.

This package will contain:
    user_preference_repository.py — crypto_user_preference table
                                    for favorites and display prefs
                                    (TASK 79.2)

Repositories live inside their owning module (not in db_manager).
They receive the app's db service via constructor and use
`db_service.connection()` to obtain a connection.
"""
