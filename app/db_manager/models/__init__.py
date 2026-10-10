"""
Data models (plain dataclasses, no ORM).

Used to transfer data between repositories, workflows and the rest of
the application without exposing raw dicts.
"""
from .user import User
from .access import Role, Form, Condition, FormAccess
from .activity import Activity

__all__ = [
    "User",
    "Role",
    "Form",
    "Condition",
    "FormAccess",
    "Activity",
]
