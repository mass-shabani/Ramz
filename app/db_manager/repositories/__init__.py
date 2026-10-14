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
FormAccessRepository    — `form_access` table
ActivityRepository      — `user_activity_log` + `activity_type`
ContactRepository       — `contact` hub
EmailRepository         — `email` table
PhoneRepository         — `phone` table
AddressRepository       — `post_address` table
"""
from .people_repository import PeopleRepository
from .user_repository import UserRepository
from .role_repository import RoleRepository
from .form_repository import FormRepository
from .condition_repository import ConditionRepository
from .form_access_repository import FormAccessRepository
from .activity_repository import ActivityRepository
from .contact_repository import ContactRepository
from .email_repository import EmailRepository
from .phone_repository import PhoneRepository
from .address_repository import AddressRepository
from .address_type_repository import AddressTypeRepository
from .phone_type_repository import PhoneTypeRepository
from .subscription_repository import SubscriptionRepository
from .bank_repository import BankRepository
from .bank_account_repository import BankAccountRepository
from .bank_card_repository import BankCardRepository
from .session_repository import SessionRepository

__all__ = [
    "PeopleRepository",
    "UserRepository",
    "RoleRepository",
    "FormRepository",
    "ConditionRepository",
    "FormAccessRepository",
    "ActivityRepository",
    "ContactRepository",
    "EmailRepository",
    "PhoneRepository",
    "AddressRepository",
    "AddressTypeRepository",
    "PhoneTypeRepository",
    "SubscriptionRepository",
    "BankRepository",
    "BankAccountRepository",
    "BankCardRepository",
    "SessionRepository",
]
