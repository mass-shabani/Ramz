"""
Shared helpers for repository operations.

The framework's DatabaseConnection uses these signatures:

    insert(table, data, returning=None)
    update(table, data, where, where_sql=None, where_params=None)
    delete(table, where, where_sql=None, where_params=None)

We wrap them here so that:

    • Our repository code reads naturally (where, values).
    • If the framework changes signatures, only this file is updated.
    • `_update_ok` and `_extract_last_insert_id` are defined once.

Every repository imports from this module.
"""
from typing import Any, Dict, Optional


# ==============================================================
# Write wrappers
# ==============================================================
async def db_insert(conn, table: str, values: Dict[str, Any]):
    """
    Framework-compatible insert.

    Our callers use `values`; the framework expects `data`.
    """
    return await conn.insert(table, data=values)


async def db_update(
    conn,
    table: str,
    where: Dict[str, Any],
    values: Dict[str, Any],
):
    """
    Framework-compatible update.

    Our callers use (table, where, values); the framework expects
    (table, data, where).
    """
    return await conn.update(table, data=values, where=where)


async def db_delete(conn, table: str, where: Dict[str, Any]):
    """Framework-compatible delete."""
    return await conn.delete(table, where=where)


# ==============================================================
# Result interpretation
# ==============================================================
def result_ok(result) -> bool:
    """
    Interpret the return value of a write operation.

    Handles:
        • None         → False
        • bool         → the bool itself
        • int          → result > 0
        • QueryResult  → result.success AND result.affected_rows > 0
    """
    if result is None:
        return False

    if isinstance(result, bool):
        return result

    if isinstance(result, int):
        return result > 0

    # QueryResult from framework
    success = getattr(result, "success", True)
    if not success:
        return False

    for attr in ("affected_rows", "rowcount", "rows_affected"):
        if hasattr(result, attr):
            try:
                return int(getattr(result, attr)) > 0
            except (TypeError, ValueError):
                continue

    # No affected_rows available but success=True → assume ok
    return True


def result_last_id(result) -> Optional[int]:
    """
    Extract last_insert_id from a write operation result.

    Handles:
        • None         → None
        • int          → the int itself
        • QueryResult  → result.last_insert_id
    """
    if result is None:
        return None

    if isinstance(result, int):
        return result

    if hasattr(result, "success") and not result.success:
        return None

    if hasattr(result, "last_insert_id"):
        try:
            value = result.last_insert_id
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            pass

    return None


# ==============================================================
# Backward-compatible aliases
# ==============================================================
# Some existing repository code calls these names. Keeping aliases
# avoids editing every call site just for the rename.
_update_ok = result_ok
_extract_last_insert_id = result_last_id
