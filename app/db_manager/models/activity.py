"""
Activity models.

Represents a single row from `user_activity_log` enriched with the
activity type name (via JOIN with `activity_type`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Activity:
    """
    One activity log entry.
    """
    activity_id: int
    user_id: int
    activity_type: str           # type_name from activity_type
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    action_time: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> "Activity":
        return cls(
            activity_id=int(row.get("activity_id") or 0),
            user_id=int(row.get("user_id") or 0),
            activity_type=row.get("type_name") or "",
            ip_address=row.get("ip_address"),
            user_agent=row.get("user_agent"),
            action_time=_parse_datetime(row.get("action_time")),
        )


# --------------------------------------------------------------
# Helper
# --------------------------------------------------------------
def _parse_datetime(value) -> Optional[datetime]:
    """Parse a datetime-like value coming from the database."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None
