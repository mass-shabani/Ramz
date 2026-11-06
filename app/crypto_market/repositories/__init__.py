"""
repositories — database access for crypto_market.

This package contains:
    symbol_map_repository.py  — crypto_symbol_map CRUD (TASK 76.9)

Repositories live inside their owning module (not in db_manager).
They receive the app's db service via constructor and use
`db_service.connection()` to obtain a connection.
"""
