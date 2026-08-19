"""
Application Database Models - Table definitions using system database types.
"""
from typing import List, Dict

def get_app_tables(db_types: Dict) -> List:
    """
    Get all table definitions for the application.
    Returns a list of TableDef objects.
    """
    # Extract types dynamically from the injected dictionary to avoid direct imports
    TableDef = db_types["TableDef"]
    ColumnDef = db_types["ColumnDef"]
    IndexDef = db_types["IndexDef"]
    ColumnType = db_types["ColumnType"]
    
    tables = []
    
    # Users table for authentication and profile management
    users_table = TableDef(
        name="users",
        columns=[
            ColumnDef(
                name="id",
                type=ColumnType.INTEGER,
                nullable=False,
                primary_key=True,
                auto_increment=True
            ),
            ColumnDef(
                name="username",
                type=ColumnType.VARCHAR,
                length=50,
                nullable=False,
                unique=True
            ),
            ColumnDef(
                name="email",
                type=ColumnType.VARCHAR,
                length=100,
                nullable=False,
                unique=True
            ),
            ColumnDef(
                name="password_hash",
                type=ColumnType.VARCHAR,
                length=255,
                nullable=False
            ),
            ColumnDef(
                name="is_active",
                type=ColumnType.BOOLEAN,
                nullable=False,
                default=True
            ),
            ColumnDef(
                name="created_at",
                type=ColumnType.DATETIME,
                nullable=False
            ),
            ColumnDef(
                name="updated_at",
                type=ColumnType.DATETIME,
                nullable=False
            )
        ],
        indexes=[
            IndexDef(
                name="idx_users_username",
                columns=["username"],
                unique=True
            ),
            IndexDef(
                name="idx_users_email",
                columns=["email"],
                unique=True
            )
        ],
        comment="Users table for authentication and profile management"
    )
    
    tables.append(users_table)
    
    # Add more tables here as the project grows
    # For example: transactions, wallet_addresses, api_keys, etc.
    
    return tables