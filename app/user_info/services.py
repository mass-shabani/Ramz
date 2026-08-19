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
            user = await self.app_db_service.get_user_by_id(user_id)
            if user:
                # Remove sensitive data before sending to template
                user.pop("password_hash", None)
                return user
            return None
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
                return False, "این ایمیل قبلاً توسط کاربر دیگری استفاده شده است."

            # Update data
            update_data = {"email": email}
            success = await self.app_db_service.update_user(user_id, update_data)
            
            if success:
                return True, "اطلاعات با موفقیت به‌روزرسانی شد."
            else:
                return False, "خطا در به‌روزرسانی اطلاعات. لطفاً دوباره تلاش کنید."
                
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error updating profile for user {user_id}: {e}", 
                              level="ERROR", tag="user_info")
            return False, "یک خطای داخلی رخ داد."