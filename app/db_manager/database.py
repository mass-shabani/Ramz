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
        """Create a table if it does not exist."""
        try:
            conn = self.database_service.get_connection(self.connection_name)
            result = await conn.create_table(table_def)
            return result.success
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error creating table {table_def.name}: {e}", level="ERROR", tag="database")
            return False

    async def _execute(self, query: str, params: tuple = ()) -> bool:
        """Execute a write query."""
        try:
            conn = self.database_service.get_connection(self.connection_name)
            result = await conn.execute(query, params)
            return result.success
        except Exception as e:
            if self.logger:
                self.logger.log(f"Database execute error: {e}", level="ERROR", tag="database")
            return False

    async def _fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute a read query and return a single row."""
        try:
            conn = self.database_service.get_connection(self.connection_name)
            return await conn.fetch_one(query, params)
        except Exception as e:
            if self.logger:
                self.logger.log(f"Database fetch_one error: {e}", level="ERROR", tag="database")
            return None

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Find user account by username with related people, role, email, and phone data."""
        query = """
            SELECT 
                u.user_id,
                u.people_id,
                u.role_id,
                u.subscription_id,
                u.email_id,
                u.phone_id,
                u.username,
                u.password_hash,
                u.xp_points,
                u.two_factor_enabled,
                u.two_factor_secret,
                u.two_factor_backup_codes,
                u.enabled,
                u.created_at,
                u.updated_at,
                p.first_name,
                p.last_name,
                p.national_code,
                p.birth_date,
                p.gender,
                r.role_name,
                e.email_address,
                ph.phone_number,
                c.contact_id
            FROM user u
            LEFT JOIN people p ON u.people_id = p.people_id
            LEFT JOIN role r ON u.role_id = r.role_id
            LEFT JOIN email e ON u.email_id = e.email_id
            LEFT JOIN phone ph ON u.phone_id = ph.phone_id
            LEFT JOIN contact c ON p.contact_id = c.contact_id
            WHERE u.username = ?
        """
        return await self._fetch_one(query, (username,))

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user account by email address."""
        query = """
            SELECT 
                u.user_id,
                u.username,
                u.password_hash,
                u.enabled,
                u.people_id,
                u.role_id,
                u.email_id,
                u.phone_id
            FROM user u
            LEFT JOIN email e ON u.email_id = e.email_id
            WHERE e.email_address = ?
        """
        return await self._fetch_one(query, (email,))

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Find user account by ID with related data."""
        return await self.get_user_by_username_from_id(user_id)

    async def get_user_by_username_from_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Find user account by user_id with related data."""
        query = """
            SELECT 
                u.user_id,
                u.people_id,
                u.role_id,
                u.subscription_id,
                u.email_id,
                u.phone_id,
                u.username,
                u.password_hash,
                u.xp_points,
                u.two_factor_enabled,
                u.two_factor_secret,
                u.two_factor_backup_codes,
                u.enabled,
                u.created_at,
                u.updated_at,
                p.first_name,
                p.last_name,
                p.national_code,
                p.birth_date,
                p.gender,
                r.role_name,
                e.email_address,
                ph.phone_number,
                c.contact_id
            FROM user u
            LEFT JOIN people p ON u.people_id = p.people_id
            LEFT JOIN role r ON u.role_id = r.role_id
            LEFT JOIN email e ON u.email_id = e.email_id
            LEFT JOIN phone ph ON u.phone_id = ph.phone_id
            LEFT JOIN contact c ON p.contact_id = c.contact_id
            WHERE u.user_id = ?
        """
        return await self._fetch_one(query, (user_id,))

    async def get_profile_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get full profile data for the profile page."""
        user = await self.get_user_by_username_from_id(user_id)
        if not user:
            return None

        contact_id = user.get("contact_id")
        address = None
        if contact_id:
            address = await self._fetch_one(
                "SELECT address_line1, address_line2, city, state_province, postal_code, country FROM post_address WHERE contact_id = ? AND enabled = 1",
                (contact_id,)
            )

        profile = {
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "email": user.get("email_address"),
            "phone": user.get("phone_number"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "full_name": (user.get("first_name", "") + " " + user.get("last_name", "")).strip(),
            "national_code": user.get("national_code"),
            "birth_date": user.get("birth_date"),
            "gender": user.get("gender"),
            "role_name": user.get("role_name"),
            "xp_points": user.get("xp_points"),
            "created_at": user.get("created_at"),
            "address": address,
        }
        return profile

    async def update_user_email(self, user_id: int, new_email: str) -> bool:
        """Update user email address."""
        user = await self.get_user_by_username_from_id(user_id)
        if not user:
            return False

        email_id = user.get("email_id")
        if not email_id:
            return False

        return await self._execute(
            "UPDATE email SET email_address = ?, updated_at = ? WHERE email_id = ?",
            (new_email, datetime.utcnow().isoformat(), email_id)
        )

    async def user_exists(self, username: str = None, email: str = None) -> bool:
        """Check if a user exists by username or email."""
        if username:
            user = await self.get_user_by_username(username)
            if user:
                return True
        if email:
            user = await self.get_user_by_email(email)
            if user:
                return True
        return False

    async def insert_user(self, username: str, email: str, password_hash: str) -> Optional[int]:
        """Insert a new user with related contact/people/email records."""
        try:
            conn = self.database_service.get_connection(self.connection_name)

            cursor = await conn.execute("BEGIN TRANSACTION;")

            # Create contact
            await conn.execute(
                "INSERT INTO contact (enabled, created_at, updated_at) VALUES (1, ?, ?)",
                (datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
            )
            contact_id = cursor.last_insert_id

            # Create people
            await conn.execute(
                "INSERT INTO people (contact_id, first_name, last_name, enabled, created_at, updated_at) VALUES (?, ?, ?, 1, ?, ?)",
                (contact_id, username, username, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
            )
            people_id = cursor.last_insert_id

            # Create email
            await conn.execute(
                "INSERT INTO email (contact_id, email_address, enabled, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
                (contact_id, email, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
            )
            email_id = cursor.last_insert_id

            # Get default role
            role = await conn.fetch_one("SELECT role_id FROM role WHERE role_name = 'user' LIMIT 1")
            role_id = role["role_id"] if role else None

            # Create user
            await conn.execute(
                """INSERT INTO user 
                   (people_id, role_id, email_id, username, password_hash, xp_points, enabled, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 0, 1, ?, ?)""",
                (people_id, role_id, email_id, username, password_hash,
                 datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
            )
            user_id = cursor.last_insert_id

            await conn.execute("COMMIT;")
            return user_id

        except Exception as e:
            if self.logger:
                self.logger.log(f"Error inserting user: {e}", level="ERROR", tag="database")
            try:
                await conn.execute("ROLLBACK;")
            except Exception:
                pass
            return None

    async def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """Update user information."""
        try:
            user = await self.get_user_by_username_from_id(user_id)
            if not user:
                return False

            allowed_fields = {"first_name", "last_name", "national_code", "birth_date", "gender"}
            people_fields = {k: v for k, v in data.items() if k in allowed_fields}

            if people_fields:
                set_clause = ", ".join([f"{k} = ?" for k in people_fields.keys()])
                values = list(people_fields.values()) + [datetime.utcnow().isoformat(), user["people_id"]]
                await self._execute(
                    f"UPDATE people SET {set_clause}, updated_at = ? WHERE people_id = ?",
                    tuple(values)
                )

            return True
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error updating user: {e}", level="ERROR", tag="database")
            return False

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        try:
            user = await self.get_user_by_username_from_id(user_id)
            if not user:
                return False

            conn = self.database_service.get_connection(self.connection_name)
            await conn.execute("BEGIN TRANSACTION;")
            await conn.execute("DELETE FROM user WHERE user_id = ?", (user_id,))
            await conn.execute("DELETE FROM people WHERE people_id = ?", (user["people_id"],))
            await conn.execute("DELETE FROM contact WHERE contact_id = ?", (user["contact_id"],))
            await conn.execute("COMMIT;")
            return True
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error deleting user: {e}", level="ERROR", tag="database")
            return False

    async def get_full_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get full profile with contact details."""
        profile = await self.get_profile_data(user_id)
        return profile
