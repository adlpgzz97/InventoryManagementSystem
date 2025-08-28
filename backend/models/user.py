"""
User model for Inventory Management System
Handles user authentication, role management, and user loading
"""

from flask_login import UserMixin
from typing import Optional, Dict, Any
import logging

from utils.database import execute_query

# Configure logging
logger = logging.getLogger(__name__)


class User(UserMixin):
    """User model for Flask-Login integration"""
    
    def __init__(self, id: str, username: str, role: str):
        self.id = id
        self.username = username
        self.role = role
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role.lower() == 'admin'
    
    @property
    def is_manager(self) -> bool:
        """Check if user has manager role"""
        return self.role.lower() == 'manager'
    
    @property
    def is_worker(self) -> bool:
        """Check if user has worker role"""
        return self.role.lower() == 'worker'
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission based on role"""
        permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'view_reports'],
            'manager': ['read', 'write', 'view_reports'],
            'worker': ['read', 'write']
        }
        
        user_permissions = permissions.get(self.role.lower(), [])
        return permission in user_permissions
    
    @classmethod
    def get_by_id(cls, user_id: str) -> Optional['User']:
        """Get user by ID"""
        try:
            result = execute_query(
                "SELECT id, username, role FROM users WHERE id = %s",
                (user_id,),
                fetch_one=True
            )
            
            if result:
                return cls(
                    id=str(result['id']),
                    username=result['username'],
                    role=result['role']
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """Get user by username"""
        try:
            result = execute_query(
                "SELECT id, username, role FROM users WHERE username = %s",
                (username,),
                fetch_one=True
            )
            
            if result:
                return cls(
                    id=str(result['id']),
                    username=result['username'],
                    role=result['role']
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional['User']:
        """Authenticate user with username and password"""
        try:
            # Get user with password hash
            result = execute_query(
                "SELECT id, username, role, password_hash FROM users WHERE username = %s",
                (username,),
                fetch_one=True
            )
            
            if result:
                # Import bcrypt here to avoid circular imports
                import bcrypt
                
                # Check password
                if bcrypt.checkpw(password.encode('utf-8'), result['password_hash'].encode('utf-8')):
                    return cls(
                        id=str(result['id']),
                        username=result['username'],
                        role=result['role']
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error authenticating user {username}: {e}")
            return None
    
    @classmethod
    def create_user(cls, username: str, password: str, role: str = 'worker') -> Optional['User']:
        """Create a new user"""
        try:
            import bcrypt
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Insert user
            result = execute_query(
                """
                INSERT INTO users (username, password_hash, role) 
                VALUES (%s, %s, %s) 
                RETURNING id, username, role
                """,
                (username, password_hash.decode('utf-8'), role),
                fetch_one=True
            )
            
            if result:
                return cls(
                    id=str(result['id']),
                    username=result['username'],
                    role=result['role']
                )
            return None
            
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            return None
    
    @classmethod
    def get_all_users(cls) -> list['User']:
        """Get all users"""
        try:
            results = execute_query(
                "SELECT id, username, role FROM users ORDER BY username",
                fetch_all=True
            )
            
            return [
                cls(
                    id=str(result['id']),
                    username=result['username'],
                    role=result['role']
                )
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'is_admin': self.is_admin,
            'is_manager': self.is_manager,
            'is_worker': self.is_worker
        }


def load_user(user_id: str) -> Optional[User]:
    """
    Load user by ID for Flask-Login
    This function is used by Flask-Login's user_loader decorator
    """
    return User.get_by_id(user_id)
