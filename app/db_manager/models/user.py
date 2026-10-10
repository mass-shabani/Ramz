"""
User model.

A plain dataclass that represents a user in the application. Used to
transfer data between repositories, workflows and the rest of the
codebase without exposing raw database dicts.

The model combines columns from the `user` table with the joined
columns from `people`, `role`, and `subscription` when available.
The `password_hash` field is populated only when the caller explicitly
requests it (e.g. during login). For most operations it is None.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """
    Represents an application user.

    The essential fields are required. Optional fields are populated
    only when the corresponding join was performed.
    """

    # --- From the `user` table ---
    user_id: int
    username: str
    enabled: bool
    role_id: int

    # --- From the joined `people` table ---
    people_id: int
    first_name: str
    last_name: str

    # --- Optional fields (populated by specific queries) ---
    email_id: Optional[int] = None
    phone_id: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role_name: Optional[str] = None
    subscription_id: Optional[int] = None
    subscription_name: Optional[str] = None

    xp_points: int = 0
    two_factor_enabled: bool = False

    # Populated only when explicitly requested (login flow)
    password_hash: Optional[str] = None

    enabled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ----------------------------------------------------------
    # Convenience properties
    # ----------------------------------------------------------
    @property
    def full_name(self) -> str:
        """Return 'First Last', trimmed."""
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(p for p in parts if p).strip() or self.username

    @property
    def initials(self) -> str:
        """Return up to two uppercase initials for avatar display."""
        first = (self.first_name or "").strip()
        last = (self.last_name or "").strip()
        if first and last:
            return (first[0] + last[0]).upper()
        if first:
            return first[:2].upper()
        return (self.username or "U")[:2].upper()

    @property
    def is_admin(self) -> bool:
        """True if the user's role is 'admin'."""
        return (self.role_name or "").lower() == "admin"

    # ----------------------------------------------------------
    # Factory
    # ----------------------------------------------------------
    @classmethod
    def from_row(cls, row: dict) -> "User":
        """
        Build a User from a database row (a dict).

        Missing keys are treated as None. Boolean-like values (0/1 in
        SQLite) are converted to proper Python bools.
        """
        get = row.get

        return cls(
            user_id=int(get("user_id")),
            username=get("username") or "",
            enabled=bool(get("enabled", 0)),
            role_id=int(get("role_id") or 0),

            people_id=int(get("people_id") or 0),
            first_name=get("first_name") or "",
            last_name=get("last_name") or "",

            email_id=get("email_id"),
            phone_id=get("phone_id"),
            email=get("email_address") or get("email"),
            phone=get("phone_number") or get("phone"),
            role_name=get("role_name"),
            subscription_id=get("subscription_id"),
            subscription_name=get("subscription_name"),

            xp_points=int(get("xp_points") or 0),
            two_factor_enabled=bool(get("two_factor_enabled", 0)),

            password_hash=get("password_hash"),

            enabled_at=_parse_datetime(get("enabled_at")),
            created_at=_parse_datetime(get("created_at")),
            updated_at=_parse_datetime(get("updated_at")),
        )


# --------------------------------------------------------------
# Helpers
# --------------------------------------------------------------
def _parse_datetime(value) -> Optional[datetime]:
    """
    Parse a datetime-like value coming from the database.

    Accepts:
        • None → returns None
        • datetime → returns as-is
        • str → tries ISO format first, then a few common variants
    """
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
