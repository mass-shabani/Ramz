"""
Workflows sub-package.

Workflows combine multiple repositories to perform business operations
(login, signup, profile retrieval, password change, …). They are the
only place where cross-table transactions and multi-step logic live.

Exports
-------
LoginWorkflow — authentication flow
"""
from .login_workflow import LoginWorkflow

__all__ = [
    "LoginWorkflow",
]
