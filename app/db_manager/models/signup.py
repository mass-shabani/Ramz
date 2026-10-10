"""
Signup data model.

Input container for the signup workflow. Only username, password,
first_name and last_name are strictly required. Everything else is
optional and will be skipped if missing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SignupData:
    """
    Data required to create a new user account.
    """
    # --- Required ---
    username:    str
    password:    str
    first_name:  str
    last_name:   str

    # --- Optional identity ---
    national_code: Optional[str] = None
    birth_date:    Optional[str] = None   # "YYYY-MM-DD"
    gender:        Optional[str] = None   # "male" | "female" | "other"

    # --- Optional contact ---
    email:         Optional[str] = None
    phone:         Optional[str] = None

    # --- Optional role override (defaults to "user" if None) ---
    role_name:     Optional[str] = None
