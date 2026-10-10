"""
Repositories sub-package.

Each repository handles CRUD operations for a single table (or a small
family of related tables). Repositories never contain business logic —
that belongs in workflows.

Exports
-------
PeopleRepository        — `people` table
UserRepository          — `user` table + joins
RoleRepository          — `role` table
FormRepository          — `form` table
ConditionRepository     — `condition_of` table
FormAccessRepository    — `form_access` table (many-to-many role↔form)
"""
from .people_repository import PeopleRepository
from .user_repository import UserRepository
from .role_repository import RoleRepository
from .form_repository import FormRepository
from .condition_repository import ConditionRepository
from .form_access_repository import FormAccessRepository

__all__ = [
    "PeopleRepository",
    "UserRepository",
    "RoleRepository",
    "FormRepository",
    "ConditionRepository",
    "FormAccessRepository",
]
