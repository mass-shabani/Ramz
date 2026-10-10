"""
Repositories sub-package.

Each repository handles CRUD operations for a single table (or a small
family of related tables). Repositories never contain business logic —
that belongs in workflows.

Exports
-------
PeopleRepository  — CRUD for the `people` table
UserRepository    — reads for the `user` table joined with related tables
"""
from .people_repository import PeopleRepository
from .user_repository import UserRepository

__all__ = [
    "PeopleRepository",
    "UserRepository",
]
