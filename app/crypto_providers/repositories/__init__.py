"""
repositories — database access for crypto_providers.

This package contains:
    credential_repository.py  — crypto_credential CRUD (TASK 78.2)

Repositories live inside their owning module (not in db_manager).
They receive the app's db service via constructor and use
`db_service.connection()` to obtain a connection.
"""
