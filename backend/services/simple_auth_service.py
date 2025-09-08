"""
Simple Authentication Service for Inventory Management System
Minimal authentication with basic CSRF protection for local use
"""

from typing import Optional, Dict, Any
import logging
import bcrypt
from flask import session
from flask_login import login_user, logout_user

from backend.models.user import User

logger = logging.getLogger(__name__)


class SimpleAuthService:
    """Simple authentication service for local use"""
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        try:
            user = User.authenticate(username, password)
            if user:
                logger.info(f"User {username} authenticated successfully")
                return user
            else:
                logger.warning(f"Authentication failed for username: {username}")
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
    def get_user_info(user: User) -> Dict[str, Any]:
        """Get user information for API responses"""
        try:
            return {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'is_admin': user.is_admin,
                'is_manager': user.is_manager,
                'is_worker': user.is_worker
            }
        except Exception as e:
            logger.error(f"Error getting user info for {user.username}: {e}")
            return {}
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a simple CSRF token"""
        import secrets
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(16)
        return session['csrf_token']
    
    @staticmethod
    def validate_csrf_token(token: str) -> bool:
        """Validate CSRF token"""
        if not token:
            return False
        
        session_token = session.get('csrf_token')
        if not session_token:
            return False
        
        return token == session_token
