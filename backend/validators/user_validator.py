"""
User validation schemas and methods.
Validates user data according to business rules.
"""

from typing import Dict, Any
import re

from .base_validator import BaseValidator
from backend.exceptions import ValidationError


class UserValidator(BaseValidator):
    """Validator for user data."""
    
    # User field constraints
    REQUIRED_FIELDS = ['username', 'password_hash', 'role']
    MAX_USERNAME_LENGTH = 50
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 255
    ALLOWED_ROLES = ['admin', 'manager', 'worker']
    
    def validate(self, data: Dict[str, Any]) -> None:
        """
        Validate user data.
        
        Args:
            data: User data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields
        self.validate_required_fields(data, self.REQUIRED_FIELDS)
        
        # Validate individual fields
        if 'username' in data:
            self.validate_username(data['username'])
        
        if 'password_hash' in data:
            self.validate_password_hash(data['password_hash'])
        
        if 'role' in data:
            self.validate_role(data['role'])
    
    def validate_username(self, username: str) -> None:
        """Validate username."""
        self.validate_string_length(username, 'username', min_length=3, max_length=self.MAX_USERNAME_LENGTH)
        
        # Username should be alphanumeric with optional underscores
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError(
                "Username must contain only letters, numbers, and underscores",
                field='username', value=username
            )
        
        # Username cannot start with a number
        if username[0].isdigit():
            raise ValidationError("Username cannot start with a number", field='username', value=username)
        
        # Check for reserved usernames
        reserved_usernames = ['admin', 'root', 'system', 'test', 'guest', 'anonymous']
        if username.lower() in reserved_usernames:
            raise ValidationError(
                f"Username '{username}' is reserved and cannot be used",
                field='username', value=username
            )
    
    def validate_password_hash(self, password_hash: str) -> None:
        """Validate password hash."""
        self.validate_string_length(password_hash, 'password_hash', min_length=self.MIN_PASSWORD_LENGTH, max_length=self.MAX_PASSWORD_LENGTH)
        
        # Password hash should look like a hash (starts with $2b$ for bcrypt)
        if not password_hash.startswith('$2b$'):
            raise ValidationError(
                "Password hash appears to be invalid (should start with $2b$)",
                field='password_hash', value=password_hash
            )
    
    def validate_role(self, role: str) -> None:
        """Validate user role."""
        if not isinstance(role, str):
            raise ValidationError("Role must be a string", field='role', value=role)
        
        if role.lower() not in self.ALLOWED_ROLES:
            raise ValidationError(
                f"Role must be one of: {', '.join(self.ALLOWED_ROLES)}",
                field='role', value=role
            )
    
    def validate_password_strength(self, password: str) -> None:
        """
        Validate password strength (for new password creation).
        
        Args:
            password: Plain text password
            
        Raises:
            ValidationError: If password is too weak
        """
        if not isinstance(password, str):
            raise ValidationError("Password must be a string", field='password', value=password)
        
        if len(password) < self.MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Password must be at least {self.MIN_PASSWORD_LENGTH} characters long",
                field='password', value=password
            )
        
        if len(password) > self.MAX_PASSWORD_LENGTH:
            raise ValidationError(
                f"Password must be no more than {self.MAX_PASSWORD_LENGTH} characters long",
                field='password', value=password
            )
        
        # Check for common weak passwords
        weak_passwords = ['password', '123456', 'qwerty', 'admin', 'letmein']
        if password.lower() in weak_passwords:
            raise ValidationError("Password is too common and easily guessable", field='password', value=password)
        
        # Check for complexity requirements
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        if not (has_letter and has_digit):
            raise ValidationError(
                "Password must contain both letters and numbers",
                field='password', value=password
            )
    
    def validate_login_credentials(self, data: Dict[str, Any]) -> None:
        """
        Validate login credentials.
        
        Args:
            data: Login data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        required_fields = ['username', 'password']
        self.validate_required_fields(data, required_fields)
        
        if 'username' in data:
            self.validate_username(data['username'])
        
        if 'password' in data:
            if not isinstance(data['password'], str) or len(data['password']) == 0:
                raise ValidationError("Password cannot be empty", field='password', value=data['password'])
    
    def validate_user_update(self, data: Dict[str, Any]) -> None:
        """
        Validate user update data.
        
        Args:
            data: User update data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        # For updates, we only validate fields that are present
        if 'username' in data:
            self.validate_username(data['username'])
        
        if 'role' in data:
            self.validate_role(data['role'])
        
        # Don't allow password updates through this method (use dedicated password change)
        if 'password_hash' in data:
            raise ValidationError(
                "Password cannot be updated through this method. Use password change endpoint.",
                field='password_hash', value=data['password_hash']
            )
