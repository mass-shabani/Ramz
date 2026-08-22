"""
Application Database Models - Table definitions using system database types.
"""
from typing import List, Dict


def get_app_tables(db_types: Dict) -> List:
    """
    Get all table definitions for the application.
    Returns a list of TableDef objects.
    """
    TableDef = db_types["TableDef"]
    ColumnDef = db_types["ColumnDef"]
    IndexDef = db_types["IndexDef"]
    ColumnType = db_types["ColumnType"]

    tables = []

    # 1. Lookup & Reference Tables
    tables.append(TableDef(
        name="role",
        columns=[
            ColumnDef(name="role_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="role_name", type=ColumnType.VARCHAR, length=50, nullable=False, unique=True),
            ColumnDef(name="description", type=ColumnType.VARCHAR, length=255),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
            ColumnDef(name="created_at", type=ColumnType.DATETIME, nullable=False),
            ColumnDef(name="updated_at", type=ColumnType.DATETIME, nullable=False),
        ],
        indexes=[
            IndexDef(name="idx_role_name", columns=["role_name"], unique=True),
        ],
    ))

    tables.append(TableDef(
        name="condition_of",
        columns=[
            ColumnDef(name="condition_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="condition_name", type=ColumnType.VARCHAR, length=50, nullable=False, unique=True),
            ColumnDef(name="description", type=ColumnType.VARCHAR, length=255),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
        ],
    ))

    tables.append(TableDef(
        name="form",
        columns=[
            ColumnDef(name="form_id", type=ColumnType.VARCHAR, length=50, primary_key=True),
            ColumnDef(name="form_name", type=ColumnType.VARCHAR, length=100, nullable=False, unique=True),
            ColumnDef(name="description", type=ColumnType.VARCHAR, length=255),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
        ],
    ))

    tables.append(TableDef(
        name="bank",
        columns=[
            ColumnDef(name="bank_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="bank_name", type=ColumnType.VARCHAR, length=100, nullable=False),
            ColumnDef(name="bank_code", type=ColumnType.VARCHAR, length=20, unique=True),
            ColumnDef(name="swift_code", type=ColumnType.VARCHAR, length=20),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
        ],
    ))

    tables.append(TableDef(
        name="subscription",
        columns=[
            ColumnDef(name="subscription_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="subscription_name", type=ColumnType.VARCHAR, length=50, nullable=False, unique=True),
            ColumnDef(name="description", type=ColumnType.VARCHAR, length=255),
            ColumnDef(name="price", type=ColumnType.INTEGER, default=0),
            ColumnDef(name="duration_days", type=ColumnType.INTEGER),
            ColumnDef(name="features", type=ColumnType.TEXT),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
            ColumnDef(name="created_at", type=ColumnType.DATETIME, nullable=False),
            ColumnDef(name="updated_at", type=ColumnType.DATETIME, nullable=False),
        ],
    ))

    tables.append(TableDef(
        name="activity_type",
        columns=[
            ColumnDef(name="activity_type_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="type_name", type=ColumnType.VARCHAR, length=50, nullable=False, unique=True),
            ColumnDef(name="description", type=ColumnType.VARCHAR, length=255),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
        ],
    ))

    # 2. Core Contact Hub
    tables.append(TableDef(
        name="contact",
        columns=[
            ColumnDef(name="contact_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
            ColumnDef(name="created_at", type=ColumnType.DATETIME, nullable=False),
            ColumnDef(name="updated_at", type=ColumnType.DATETIME, nullable=False),
        ],
    ))

    # 3. People Table
    tables.append(TableDef(
        name="people",
        columns=[
            ColumnDef(name="people_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="contact_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="first_name", type=ColumnType.VARCHAR, length=100, nullable=False),
            ColumnDef(name="last_name", type=ColumnType.VARCHAR, length=100, nullable=False),
            ColumnDef(name="national_code", type=ColumnType.VARCHAR, length=20, unique=True),
            ColumnDef(name="birth_date", type=ColumnType.DATE),
            ColumnDef(name="gender", type=ColumnType.VARCHAR, length=10),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
            ColumnDef(name="created_at", type=ColumnType.DATETIME, nullable=False),
            ColumnDef(name="updated_at", type=ColumnType.DATETIME, nullable=False),
        ],
        indexes=[
            IndexDef(name="idx_people_contact_id", columns=["contact_id"]),
            IndexDef(name="idx_people_national_code", columns=["national_code"], unique=True),
        ],
    ))

    # 4. Users & Authentication
    tables.append(TableDef(
        name="user",
        columns=[
            ColumnDef(name="user_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="people_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="role_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="subscription_id", type=ColumnType.INTEGER),
            ColumnDef(name="email_id", type=ColumnType.INTEGER),
            ColumnDef(name="phone_id", type=ColumnType.INTEGER),
            ColumnDef(name="username", type=ColumnType.VARCHAR, length=50, nullable=False, unique=True),
            ColumnDef(name="password_hash", type=ColumnType.VARCHAR, length=255, nullable=False),
            ColumnDef(name="xp_points", type=ColumnType.INTEGER, default=0),
            ColumnDef(name="two_factor_enabled", type=ColumnType.BOOLEAN, nullable=False, default=False),
            ColumnDef(name="two_factor_secret", type=ColumnType.VARCHAR, length=255),
            ColumnDef(name="two_factor_backup_codes", type=ColumnType.TEXT),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
            ColumnDef(name="created_at", type=ColumnType.DATETIME, nullable=False),
            ColumnDef(name="updated_at", type=ColumnType.DATETIME, nullable=False),
        ],
        indexes=[
            IndexDef(name="idx_user_username", columns=["username"], unique=True),
            IndexDef(name="idx_user_role_id", columns=["role_id"]),
            IndexDef(name="idx_user_subscription_id", columns=["subscription_id"]),
            IndexDef(name="idx_user_email_id", columns=["email_id"]),
            IndexDef(name="idx_user_phone_id", columns=["phone_id"]),
        ],
    ))

    tables.append(TableDef(
        name="user_activity_log",
        columns=[
            ColumnDef(name="activity_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="user_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="activity_type_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="ip_address", type=ColumnType.VARCHAR, length=45),
            ColumnDef(name="user_agent", type=ColumnType.TEXT),
            ColumnDef(name="action_time", type=ColumnType.DATETIME, nullable=False),
        ],
        indexes=[
            IndexDef(name="idx_user_activity_user_id", columns=["user_id"]),
            IndexDef(name="idx_user_activity_type_id", columns=["activity_type_id"]),
        ],
    ))

    tables.append(TableDef(
        name="form_access",
        columns=[
            ColumnDef(name="role_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="form_id", type=ColumnType.VARCHAR, length=50, nullable=False),
            ColumnDef(name="condition_id", type=ColumnType.INTEGER, nullable=False),
        ],
        indexes=[
            IndexDef(name="idx_form_access_role_id", columns=["role_id"]),
        ],
    ))

    # 5. Contact Information
    tables.append(TableDef(
        name="phone",
        columns=[
            ColumnDef(name="phone_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="contact_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="phone_number", type=ColumnType.VARCHAR, length=20, nullable=False),
            ColumnDef(name="phone_type", type=ColumnType.VARCHAR, length=20, default="mobile"),
            ColumnDef(name="is_verified", type=ColumnType.BOOLEAN, nullable=False, default=False),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
            ColumnDef(name="created_at", type=ColumnType.DATETIME, nullable=False),
            ColumnDef(name="updated_at", type=ColumnType.DATETIME, nullable=False),
        ],
        indexes=[
            IndexDef(name="idx_phone_contact_id", columns=["contact_id"]),
        ],
    ))

    tables.append(TableDef(
        name="post_address",
        columns=[
            ColumnDef(name="address_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="contact_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="address_line1", type=ColumnType.VARCHAR, length=255, nullable=False),
            ColumnDef(name="address_line2", type=ColumnType.VARCHAR, length=255),
            ColumnDef(name="city", type=ColumnType.VARCHAR, length=100),
            ColumnDef(name="state_province", type=ColumnType.VARCHAR, length=100),
            ColumnDef(name="postal_code", type=ColumnType.VARCHAR, length=20),
            ColumnDef(name="country", type=ColumnType.VARCHAR, length=100, default="Iran"),
            ColumnDef(name="address_type", type=ColumnType.VARCHAR, length=20, default="home"),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
            ColumnDef(name="created_at", type=ColumnType.DATETIME, nullable=False),
            ColumnDef(name="updated_at", type=ColumnType.DATETIME, nullable=False),
        ],
        indexes=[
            IndexDef(name="idx_post_address_contact_id", columns=["contact_id"]),
        ],
    ))

    tables.append(TableDef(
        name="email",
        columns=[
            ColumnDef(name="email_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="contact_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="email_address", type=ColumnType.VARCHAR, length=255, nullable=False),
            ColumnDef(name="is_verified", type=ColumnType.BOOLEAN, nullable=False, default=False),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
            ColumnDef(name="created_at", type=ColumnType.DATETIME, nullable=False),
            ColumnDef(name="updated_at", type=ColumnType.DATETIME, nullable=False),
        ],
        indexes=[
            IndexDef(name="idx_email_contact_id", columns=["contact_id"]),
        ],
    ))

    # 6. Banking Information
    tables.append(TableDef(
        name="bank_account",
        columns=[
            ColumnDef(name="bank_account_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="contact_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="bank_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="account_number", type=ColumnType.VARCHAR, length=50, nullable=False),
            ColumnDef(name="account_name", type=ColumnType.VARCHAR, length=100, nullable=False),
            ColumnDef(name="iban", type=ColumnType.VARCHAR, length=30, unique=True),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
            ColumnDef(name="created_at", type=ColumnType.DATETIME, nullable=False),
            ColumnDef(name="updated_at", type=ColumnType.DATETIME, nullable=False),
        ],
        indexes=[
            IndexDef(name="idx_bank_account_contact_id", columns=["contact_id"]),
        ],
    ))

    tables.append(TableDef(
        name="bank_card",
        columns=[
            ColumnDef(name="bank_card_id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True),
            ColumnDef(name="bank_account_id", type=ColumnType.INTEGER, nullable=False),
            ColumnDef(name="card_number", type=ColumnType.VARCHAR, length=20, nullable=False, unique=True),
            ColumnDef(name="card_holder_name", type=ColumnType.VARCHAR, length=100, nullable=False),
            ColumnDef(name="expiry_date", type=ColumnType.DATE),
            ColumnDef(name="enabled", type=ColumnType.BOOLEAN, nullable=False, default=True),
            ColumnDef(name="created_at", type=ColumnType.DATETIME, nullable=False),
            ColumnDef(name="updated_at", type=ColumnType.DATETIME, nullable=False),
        ],
        indexes=[
            IndexDef(name="idx_bank_card_account_id", columns=["bank_account_id"]),
        ],
    ))

    return tables
