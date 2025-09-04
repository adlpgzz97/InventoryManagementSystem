"""
User model for Inventory Management System
Pure data container with basic CRUD operations
"""

from flask_login import UserMixin
from typing import Optional, Dict, Any, List
import logging
import bcrypt

from backend.models.base_model import BaseModel
from backend.utils.database import execute_query

# Configure logging
logger = logging.getLogger(__name__)


class User(UserMixin, BaseModel):
    """User model - data container only"""
    
    def __init__(self, id: str, username: str, role: str):
        self.id = id
        self.username = username
        self.role = role
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role - basic computed property"""
        return self.role.lower() == 'admin'
    
    @property
    def is_manager(self) -> bool:
        """Check if user has manager role - basic computed property"""
        return self.role.lower() == 'manager'
    
    @property
    def is_worker(self) -> bool:
        """Check if user has worker role - basic computed property"""
        return self.role.lower() == 'worker'
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User instance from dictionary"""
        return cls(
            id=str(data['id']),
            username=data['username'],
            role=data['role']
        )
    
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
    
    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional['User']:
        """Authenticate user with username and password"""
        try:
            # Use timeout version to prevent freezing
            from backend.utils.database import execute_query_with_timeout

            logger.info(f"Authenticating user: {username}")

            result = execute_query_with_timeout(
                "SELECT id, username, password_hash, role FROM users WHERE username = %s",
                (username,),
                fetch_one=True,
                timeout=10  # Increased timeout for login
            )

            if result and result['password_hash']:
                logger.info(f"User {username} found, verifying password...")
                # Verify password using bcrypt
                password_verified = bcrypt.checkpw(
                    password.encode('utf-8'),
                    result['password_hash'].encode('utf-8')
                )

                if password_verified:
                    logger.info(f"User {username} authenticated successfully")
                    return cls.from_dict(result)
                else:
                    logger.warning(f"Invalid password for user {username}")
                    return None
            else:
                logger.warning(f"User {username} not found")
                return None

        except Exception as e:
            logger.error(f"Error during authentication for {username}: {e}")
            return None
    
    @classmethod
    def get_by_id(cls, user_id: str) -> Optional['User']:
        """Get user by ID - basic CRUD operation"""
        try:
            result = execute_query(
                "SELECT id, username, role FROM users WHERE id = %s",
                (user_id,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """Get user by username - basic CRUD operation"""
        try:
            result = execute_query(
                "SELECT id, username, role FROM users WHERE username = %s",
                (username,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    @classmethod
    def get_all(cls) -> List['User']:
        """Get all users - basic CRUD operation"""
        try:
            results = execute_query(
                "SELECT id, username, role FROM users ORDER BY username",
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    @classmethod
    def create(cls, username: str, password_hash: str, role: str = 'worker') -> Optional['User']:
        """Create a new user - basic CRUD operation"""
        try:
            result = execute_query(
                """
                INSERT INTO users (username, password_hash, role) 
                VALUES (%s, %s, %s) 
                RETURNING id, username, role
                """,
                (username, password_hash, role),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    @classmethod
    def create_user(cls, username: str, password: str, role: str = 'worker') -> Optional['User']:
        """Create a new user with password hashing"""
        try:
            # Hash the password using bcrypt
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Create the user
            return cls.create(username, password_hash, role)
            
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            return None
    
    def update(self, **kwargs) -> bool:
        """Update user attributes - basic CRUD operation"""
        try:
            # Build dynamic update query
            fields = []
            values = []
            
            for key, value in kwargs.items():
                if hasattr(self, key):
                    fields.append(f"{key} = %s")
                    values.append(value)
            
            if not fields:
                return False
            
            values.append(self.id)
            
            query = f"""
                UPDATE users 
                SET {', '.join(fields)}
                WHERE id = %s
                RETURNING id
            """
            
            result = execute_query(query, tuple(values), fetch_one=True)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error updating user {self.id}: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete the user - basic CRUD operation"""
        try:
            result = execute_query(
                "DELETE FROM users WHERE id = %s RETURNING id",
                (self.id,),
                fetch_one=True
            )
            return result is not None
            
        except Exception as e:
            logger.error(f"Error deleting user {self.id}: {e}")
            return False
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission based on role"""
        try:
            if self.is_admin:
                return True  # Admin has all permissions
            elif self.is_manager:
                # Manager permissions
                manager_permissions = ['read', 'write', 'view_reports']
                return permission in manager_permissions
            elif self.is_worker:
                # Worker permissions
                worker_permissions = ['read']
                return permission in worker_permissions
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error checking permission for user {self.username}: {e}")
            return False


def load_user(user_id: str) -> Optional[User]:
    """
    Load user by ID for Flask-Login
    This function is used by Flask-Login's user_loader decorator
    """
    return User.get_by_id(user_id)
