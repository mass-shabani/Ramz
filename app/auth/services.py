"""
Auth Service - Handles business logic for authentication.
"""
import hashlib
from typing import Optional, Dict, Any


class AuthService:
    """
    Provides authentication methods using the app_db_service.
    """
    
    def __init__(self, app_db_service: Any, logger: Any):
        self.app_db_service = app_db_service
        self.logger = logger

    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256 (For production, use bcrypt/argon2)."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    async def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verify username and password.
        Returns user dict if successful, None otherwise.
        """
        try:
            password_hash = self._hash_password(password)
            user = await self.app_db_service.get_user_by_username(username)
            
            if user and user.get("password_hash") == password_hash:
                if user.get("is_active"):
                    return user
                else:
                    if self.logger:
                        self.logger.log(f"Login attempt for inactive user: {username}", level="WARNING", tag="auth")
                    return None
            return None
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error during authentication: {e}", level="ERROR", tag="auth")
            return None