"""
Base Service Class for Inventory Management System
Provides common patterns and error handling for business logic services
"""

import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Base exception for service layer errors"""
    pass


class ValidationError(ServiceError):
    """Raised when input validation fails"""
    pass


class NotFoundError(ServiceError):
    """Raised when a requested resource is not found"""
    pass


class BaseService(ABC):
    """Base service class with common patterns"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def log_operation(self, operation: str, details: Dict[str, Any] = None):
        """Log service operations for audit purposes"""
        if details:
            self.logger.info(f"{operation}: {details}")
        else:
            self.logger.info(operation)
    
    def log_error(self, operation: str, error: Exception, details: Dict[str, Any] = None):
        """Log service errors with context"""
        error_msg = f"Error in {operation}: {str(error)}"
        if details:
            error_msg += f" | Details: {details}"
        self.logger.error(error_msg)
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate that required fields are present in data"""
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValidationError(f"Missing required field: {missing_fields[0]}")
    
    def validate_field_type(self, data: Dict[str, Any], field: str, expected_type: type) -> None:
        """Validate that a field has the expected type"""
        if field in data and not isinstance(data[field], expected_type):
            raise ValidationError(f"Field '{field}' must be of type {expected_type.__name__}")
    
    def validate_field_range(self, data: Dict[str, Any], field: str, min_value: Any = None, max_value: Any = None) -> None:
        """Validate that a field value is within the specified range"""
        if field in data:
            value = data[field]
            if min_value is not None and value < min_value:
                raise ValidationError(f"Field '{field}' must be >= {min_value}")
            if max_value is not None and value > max_value:
                raise ValidationError(f"Field '{field}' must be <= {max_value}")
    
    def sanitize_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize input data to prevent injection attacks"""
        from backend.utils.simple_security import SimpleSecurityUtils
        # Simple sanitization for local use
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = SimpleSecurityUtils.sanitize_input(value)
            else:
                sanitized[key] = value
        return sanitized
    
    def handle_database_error(self, operation: str, error: Exception) -> None:
        """Handle database errors consistently"""
        self.log_error(operation, error)
        if "connection" in str(error).lower():
            raise ServiceError("Database connection failed")
        elif "permission" in str(error).lower():
            raise ServiceError("Insufficient permissions for this operation")
        else:
            raise ServiceError(f"Database operation failed: {str(error)}")
    
    def create_response(self, success: bool, data: Any = None, message: str = "", error: str = "") -> Dict[str, Any]:
        """Create consistent response format"""
        response = {
            "success": success,
            "timestamp": self._get_timestamp()
        }
        
        if success:
            if data is not None:
                response["data"] = data
            if message:
                response["message"] = message
        else:
            if error:
                response["error"] = error
        
        return response
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_service_name(self) -> str:
        """Return the name of this service for logging and identification"""
        return self.__class__.__name__
    
    def _validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate that required fields are present in data"""
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValidationError(f"Missing required field: {missing_fields[0]}")
    
    def _format_response(self, success: bool, data: Any = None, message: str = "", error: str = "") -> Dict[str, Any]:
        """Create consistent response format"""
        response = {
            "success": success,
            "timestamp": self._get_timestamp()
        }
        
        if success:
            if data is not None:
                response["data"] = data
            if message:
                response["message"] = message
        else:
            if error:
                response["error"] = error
        
        return response
