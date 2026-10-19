"""
Access control models.

Plain dataclasses for rows from the access-related tables:
`role`, `form`, `condition_of`, `form_access`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Role:
    role_id: str
    role_name: str
    description: str = ""
    enabled: bool = True

    @classmethod
    def from_row(cls, row: dict) -> "Role":
        return cls(
            role_id=row.get("role_id") or "",
            role_name=row.get("role_name") or "",
            description=row.get("description") or "",
            enabled=bool(row.get("enabled", 1)),
        )


@dataclass
class Form:
    form_id: str
    form_name: str
    description: str = ""
    enabled: bool = True

    @classmethod
    def from_row(cls, row: dict) -> "Form":
        return cls(
            form_id=row.get("form_id") or "",
            form_name=row.get("form_name") or "",
            description=row.get("description") or "",
            enabled=bool(row.get("enabled", 1)),
        )


@dataclass
class Condition:
    condition_id: str
    condition_name: str
    description: str = ""
    enabled: bool = True

    @classmethod
    def from_row(cls, row: dict) -> "Condition":
        return cls(
            condition_id=row.get("condition_id") or "",
            condition_name=row.get("condition_name") or "",
            description=row.get("description") or "",
            enabled=bool(row.get("enabled", 1)),
        )


@dataclass
class FormAccess:
    """
    One row from `form_access`, optionally enriched with `form_name`
    and `condition_name` when the JOIN was performed.
    """
    role_id: str
    form_id: str
    condition_id: str
    form_name: Optional[str] = None
    condition_name: Optional[str] = None

    @classmethod
    def from_row(cls, row: dict) -> "FormAccess":
        return cls(
            role_id=row.get("role_id") or "",
            form_id=row.get("form_id") or "",
            condition_id=row.get("condition_id") or "",
            form_name=row.get("form_name"),
            condition_name=row.get("condition_name"),
        )
