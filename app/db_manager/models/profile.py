"""
Profile model.

Rich aggregated view of a user's complete profile, combining data
from multiple tables: user, people, role, subscription, email, phone,
and post_address.

Used by the profile page and the account settings page.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Profile:
    """
    Complete profile view for a user.
    """

    # --- From `user` ---
    user_id: int
    username: str
    enabled: bool
    xp_points: int = 0
    two_factor_enabled: bool = False
    created_at: Optional[datetime] = None

    # --- From `people` ---
    people_id: int = 0
    contact_id: int = 0
    first_name: str = ""
    last_name: str = ""
    national_code: Optional[str] = None
    birth_date: Optional[datetime] = None
    gender: Optional[str] = None

    # --- From `role` ---
    role_id: str = ""       # was int
    role_name: str = ""
    role_rank: int = 0

    # --- From `subscription` ---
    subscription_id: Optional[int] = None
    subscription_name: Optional[str] = None

    # --- From `email` (primary, via user.email_id) ---
    email_id: Optional[int] = None
    email: Optional[str] = None
    email_verified: bool = False

    # --- From `phone` (primary, via user.phone_id) ---
    phone_id: Optional[int] = None
    phone: Optional[str] = None
    phone_verified: bool = False

    # --- From `post_address` (primary / home) ---
    address_id: Optional[int] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    # ----------------------------------------------------------
    # Convenience properties
    # ----------------------------------------------------------
    @property
    def full_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(p for p in parts if p).strip() or self.username

    @property
    def initials(self) -> str:
        first = (self.first_name or "").strip()
        last = (self.last_name or "").strip()
        if first and last:
            return (first[0] + last[0]).upper()
        if first:
            return first[:2].upper()
        return (self.username or "U")[:2].upper()

    @property
    def is_admin(self) -> bool:
        return self.role_id == "admin"

    @property
    def has_address(self) -> bool:
        return bool(self.address_line1)
