"""
Application Database Manager - Wrapper around system database service for app-specific operations.
"""
from typing import Optional, Dict, Any
from datetime import datetime

class AppDatabaseManager:
    """
    Provides high-level database operations for the application using system database service.
    Other modules (like auth, user_info) should use this service instead of database_service directly.
    """
    def __init__(self, database_service, logger):
        self.database_service = database_service
        self.logger = logger
        self.connection_name = "default"

    async def create_table(self, table_def) -> bool:
        """
        Create a table if it doesn't exist.
        """
        try:
            conn = self.database_service.get_connection(self.connection_name)
            result = await conn.create_table(table_def)
            return result.success
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error creating table {table_def.name}: {e}", level="ERROR", tag="database")
            return False

    async def insert_user(self, username: str, email: str, password_hash: str) -> Optional[int]:
        """
        Insert a new user record.
        Returns the user ID if successful, None otherwise.
        """
        try:
            data = {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            # Using convenience method on database_service
            result = await self.database_service.insert(
                "users", 
                data, 
                returning=["id"],
                connection=self.connection_name
            )
            if result.success and result.data:
                return result.data[0].get("id") if isinstance(result.data, list) else result.data.get("id")
            return None
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error inserting user: {e}", level="ERROR", tag="database")
            return None

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by username.
        """
        try:
            return await self.database_service.find_one(
                "users",
                where={"username": username},
                connection=self.connection_name
            )
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error finding user by username: {e}", level="ERROR", tag="database")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by email.
        """
        try:
            return await self.database_service.find_one(
                "users",
                where={"email": email},
                connection=self.connection_name
            )
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error finding user by email: {e}", level="ERROR", tag="database")
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Find a user by ID.
        """
        try:
            return await self.database_service.find_one(
                "users",
                where={"id": user_id},
                connection=self.connection_name
            )
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error finding user by ID: {e}", level="ERROR", tag="database")
            return None

    async def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """
        Update user information.
        """
        try:
            data["updated_at"] = datetime.utcnow().isoformat()
            result = await self.database_service.update(
                "users",
                data,
                where={"id": user_id},
                connection=self.connection_name
            )
            return result.success
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error updating user: {e}", level="ERROR", tag="database")
            return False

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.
        """
        try:
            result = await self.database_service.delete(
                "users",
                where={"id": user_id},
                connection=self.connection_name
            )
            return result.success
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error deleting user: {e}", level="ERROR", tag="database")
            return False

    async def user_exists(self, username: str = None, email: str = None) -> bool:
        """
        Check if a user exists by username or email.
        """
        try:
            # Getting connection directly for operations not explicitly wrapped in service convenience methods
            conn = self.database_service.get_connection(self.connection_name)
            where = {}
            if username:
                where["username"] = username
            if email:
                where["email"] = email
            return await conn.exists("users", where=where)
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error checking user existence: {e}", level="ERROR", tag="database")
            return False