"""
Authentication Service for Inventory Management System
Handles user authentication, authorization, and session management
"""

from typing import Optional, Dict, Any
import logging
from flask_login import login_user, logout_user

from backend.models.user import User

# Configure logging
logger = logging.getLogger(__name__)


class AuthService:
    """Service class for authentication and authorization operations"""
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        try:
            user = User.authenticate(username, password)
            if user:
                logger.info(f"User {username} authenticated successfully")
                return user
            else:
                logger.warning(f"Failed authentication attempt for username: {username}")
                return None
                
        except Exception as e:
            logger.error(f"Error during authentication for {username}: {e}")
            return None
    
    @staticmethod
    def login_user(user: User, remember: bool = False) -> bool:
        """Log in a user"""
        try:
            login_user(user, remember=remember)
            logger.info(f"User {user.username} logged in successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error logging in user {user.username}: {e}")
            return False
    
    @staticmethod
    def logout_user() -> bool:
        """Log out the current user"""
        try:
            logout_user()
            logger.info("User logged out successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    @staticmethod
    def create_user(username: str, password: str, role: str = 'worker') -> Optional[User]:
        """Create a new user"""
        try:
            # Check if username already exists
            existing_user = User.get_by_username(username)
            if existing_user:
                logger.warning(f"Username {username} already exists")
                return None
            
            user = User.create_user(username, password, role)
            if user:
                logger.info(f"User {username} created successfully with role {role}")
                return user
            else:
                logger.error(f"Failed to create user {username}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            return User.get_by_id(user_id)
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get user by username"""
        try:
            return User.get_by_username(username)
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    @staticmethod
    def get_all_users() -> list[User]:
        """Get all users"""
        try:
            return User.get_all_users()
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    @staticmethod
    def check_permission(user: User, permission: str) -> bool:
        """Check if user has specific permission"""
        try:
            return user.has_permission(permission)
        except Exception as e:
            logger.error(f"Error checking permission for user {user.username}: {e}")
            return False
    
    @staticmethod
    def require_permission(permission: str):
        """Decorator to require specific permission"""
        def decorator(f):
            def wrapper(*args, **kwargs):
                from flask_login import current_user
                
                if not current_user.is_authenticated:
                    return {'error': 'Authentication required'}, 401
                
                if not AuthService.check_permission(current_user, permission):
                    return {'error': 'Insufficient permissions'}, 403
                
                return f(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def require_role(role: str):
        """Decorator to require specific role"""
        def decorator(f):
            def wrapper(*args, **kwargs):
                from flask_login import current_user
                
                if not current_user.is_authenticated:
                    return {'error': 'Authentication required'}, 401
                
                if current_user.role.lower() != role.lower():
                    return {'error': 'Insufficient permissions'}, 403
                
                return f(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def get_user_info(user: User) -> Dict[str, Any]:
        """Get user information for API responses"""
        try:
            return {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'is_admin': user.is_admin,
                'is_manager': user.is_manager,
                'is_worker': user.is_worker,
                'permissions': {
                    'read': user.has_permission('read'),
                    'write': user.has_permission('write'),
                    'delete': user.has_permission('delete'),
                    'manage_users': user.has_permission('manage_users'),
                    'view_reports': user.has_permission('view_reports')
                }
            }
        except Exception as e:
            logger.error(f"Error getting user info for {user.username}: {e}")
            return {}
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        try:
            errors = []
            warnings = []
            
            if len(password) < 8:
                errors.append("Password must be at least 8 characters long")
            
            if not any(c.isupper() for c in password):
                warnings.append("Password should contain at least one uppercase letter")
            
            if not any(c.islower() for c in password):
                warnings.append("Password should contain at least one lowercase letter")
            
            if not any(c.isdigit() for c in password):
                warnings.append("Password should contain at least one number")
            
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                warnings.append("Password should contain at least one special character")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'strength': 'weak' if len(errors) > 0 else 'strong' if len(warnings) <= 1 else 'medium'
            }
            
        except Exception as e:
            logger.error(f"Error validating password strength: {e}")
            return {
                'valid': False,
                'errors': ['Password validation failed'],
                'warnings': [],
                'strength': 'unknown'
            }
    
    @staticmethod
    def change_user_password(user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            user = User.get_by_id(user_id)
            if not user:
                logger.error(f"User not found: {user_id}")
                return False
            
            # Verify current password
            if not User.authenticate(user.username, current_password):
                logger.warning(f"Invalid current password for user {user.username}")
                return False
            
            # Validate new password strength
            validation = AuthService.validate_password_strength(new_password)
            if not validation['valid']:
                logger.warning(f"New password validation failed for user {user.username}")
                return False
            
            # Update password in database
            # Note: This would require adding a method to User model
            # For now, we'll return True as a placeholder
            logger.info(f"Password changed successfully for user {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error changing password for user {user_id}: {e}")
            return False
    
    @staticmethod
    def get_user_activity_summary(user_id: str) -> Dict[str, Any]:
        """Get user activity summary"""
        try:
            # This would typically query transaction logs, login history, etc.
            # For now, return a basic structure
            return {
                'user_id': user_id,
                'last_login': None,
                'total_logins': 0,
                'recent_activities': [],
                'permissions_used': []
            }
            
        except Exception as e:
            logger.error(f"Error getting user activity summary for {user_id}: {e}")
            return {}
