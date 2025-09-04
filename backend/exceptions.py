"""
Custom exception classes for the Inventory Management System.
Provides consistent error handling across all application layers.
"""

from typing import Optional, Dict, Any


class InventoryAppException(Exception):
    """Base exception for inventory application."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GENERAL_ERROR"
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format for API responses."""
        return {
            'error': self.message,
            'error_code': self.error_code,
            'details': self.details
        }


class ValidationError(InventoryAppException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
        self.value = value
        if field:
            self.details['field'] = field
        if value is not None:
            self.details['value'] = value


class DatabaseError(InventoryAppException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None, table: Optional[str] = None):
        super().__init__(message, "DATABASE_ERROR")
        self.operation = operation
        self.table = table
        if operation:
            self.details['operation'] = operation
        if table:
            self.details['table'] = table


class ConnectionError(InventoryAppException):
    """Raised when database connection fails."""
    
    def __init__(self, message: str, connection_type: Optional[str] = None):
        super().__init__(message, "CONNECTION_ERROR")
        self.connection_type = connection_type
        if connection_type:
            self.details['connection_type'] = connection_type


class NotFoundError(InventoryAppException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message, "NOT_FOUND")
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details['resource_type'] = resource_type
        self.details['resource_id'] = resource_id


class AuthenticationError(InventoryAppException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR")


class AuthorizationError(InventoryAppException):
    """Raised when user lacks permission for an operation."""
    
    def __init__(self, message: str = "Insufficient permissions", required_role: Optional[str] = None):
        super().__init__(message, "AUTHORIZATION_ERROR")
        self.required_role = required_role
        if required_role:
            self.details['required_role'] = required_role


class BusinessLogicError(InventoryAppException):
    """Raised when business logic rules are violated."""
    
    def __init__(self, message: str, rule: Optional[str] = None):
        super().__init__(message, "BUSINESS_LOGIC_ERROR")
        self.rule = rule
        if rule:
            self.details['rule'] = rule


class ConfigurationError(InventoryAppException):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message, "CONFIGURATION_ERROR")
        self.config_key = config_key
        if config_key:
            self.details['config_key'] = config_key


class ExternalServiceError(InventoryAppException):
    """Raised when external service calls fail."""
    
    def __init__(self, message: str, service: str, status_code: Optional[int] = None):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR")
        self.service = service
        self.status_code = status_code
        self.details['service'] = service
        if status_code:
            self.details['status_code'] = status_code
