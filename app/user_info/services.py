"""
User Info Service - Handles business logic for profile management.
"""
from typing import Optional, Dict, Any, Tuple


class UserInfoService:
    """
    Provides methods to fetch and update user profile information.
    """
    
    def __init__(self, app_db_service: Any, logger: Any):
        self.app_db_service = app_db_service
        self.logger = logger

    async def get_profile_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch user profile data by ID.
        """
        try:
            profile = await self.app_db_service.get_profile_data(user_id)
            return profile
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error fetching profile data for user {user_id}: {e}", 
                              level="ERROR", tag="user_info")
            return None

    async def update_profile(self, user_id: int, email: str) -> Tuple[bool, str]:
        """
        Update user profile information.
        Returns a tuple of (success: bool, message: str).
        """
        try:
            # Check if email is already taken by another user
            existing_user = await self.app_db_service.get_user_by_email(email)
            if existing_user and existing_user["id"] != user_id:
                return False, "This email is already used by another user."

            # Update data
            success = await self.app_db_service.update_user_email(user_id, email)
            
            if success:
                return True, "Information updated successfully."
            else:
                return False, "Error updating information. Please try again."
                
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error updating profile for user {user_id}: {e}", 
                              level="ERROR", tag="user_info")
            return False, "An internal error occurred."