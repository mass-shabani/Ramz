"""
Access control models.

Plain dataclasses for rows from the access-related tables:
`role`, `form`, `form_access`.
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
    rank: int = 0
    lock: bool = False

    @classmethod
    def from_row(cls, row: dict) -> "Role":
        return cls(
            role_id=row.get("role_id") or "",
            role_name=row.get("role_name") or "",
            description=row.get("description") or "",
            enabled=bool(row.get("enabled", 1)),
            rank=int(row.get("rank") or 0),
            lock=bool(row.get("lock", 0)),
        )


@dataclass
class Form:
    form_id: str
    form_name: str
    description: str = ""
    lock: bool = False

    @classmethod
    def from_row(cls, row: dict) -> "Form":
        return cls(
            form_id=row.get("form_id") or "",
            form_name=row.get("form_name") or "",
            description=row.get("description") or "",
            lock=bool(row.get("lock", 0)),
        )


@dataclass
class FormAccess:
    """
    One row from `form_access`, optionally enriched with `form_name`
    when the JOIN was performed.

    `level` semantics:
        0 = Closed (no access, regardless of caller's min_level)
        ≥1 = Open; higher values = more privileged levels
    """
    role_id: str
    form_id: str
    level: int
    form_name: Optional[str] = None

    @classmethod
    def from_row(cls, row: dict) -> "FormAccess":
        return cls(
            role_id=row.get("role_id") or "",
            form_id=row.get("form_id") or "",
            level=int(row.get("level") or 0),
            form_name=row.get("form_name"),
        )
