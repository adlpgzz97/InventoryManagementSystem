"""
Base validator class providing common validation methods and decorators.
All entity-specific validators should inherit from this class.
"""

import functools
import re
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, date

from backend.exceptions import ValidationError


class BaseValidator:
    """Base class for all validators with common validation methods."""
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        Validate that all required fields are present and not empty.
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
            
        Raises:
            ValidationError: If any required field is missing or empty
        """
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}", field=field)
            
            value = data[field]
            if value is None or (isinstance(value, str) and value.strip() == ''):
                raise ValidationError(f"Required field '{field}' cannot be empty", field=field, value=value)
    
    @staticmethod
    def validate_string_length(value: str, field: str, min_length: int = 1, max_length: int = 255) -> None:
        """
        Validate string length constraints.
        
        Args:
            value: String value to validate
            field: Field name for error reporting
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            
        Raises:
            ValidationError: If length constraints are violated
        """
        if not isinstance(value, str):
            raise ValidationError(f"Field '{field}' must be a string", field=field, value=value)
        
        if len(value) < min_length:
            raise ValidationError(
                f"Field '{field}' must be at least {min_length} characters long",
                field=field, value=value
            )
        
        if len(value) > max_length:
            raise ValidationError(
                f"Field '{field}' must be no more than {max_length} characters long",
                field=field, value=value
            )
    
    @staticmethod
    def validate_email(email: str, field: str = "email") -> None:
        """
        Validate email format.
        
        Args:
            email: Email string to validate
            field: Field name for error reporting
            
        Raises:
            ValidationError: If email format is invalid
        """
        if not email:
            return  # Allow empty emails if not required
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(f"Invalid email format for field '{field}'", field=field, value=email)
    
    @staticmethod
    def validate_phone(phone: str, field: str = "phone") -> None:
        """
        Validate phone number format.
        
        Args:
            phone: Phone string to validate
            field: Field name for error reporting
            
        Raises:
            ValidationError: If phone format is invalid
        """
        if not phone:
            return  # Allow empty phones if not required
        
        # Remove common separators and validate
        clean_phone = re.sub(r'[\s\-\(\)\.]', '', phone)
        if not re.match(r'^\+?[0-9]{7,15}$', clean_phone):
            raise ValidationError(f"Invalid phone format for field '{field}'", field=field, value=phone)
    
    @staticmethod
    def validate_uuid(uuid_value: str, field: str) -> None:
        """
        Validate UUID format.
        
        Args:
            uuid_value: UUID string to validate
            field: Field name for error reporting
            
        Raises:
            ValidationError: If UUID format is invalid
        """
        if not uuid_value:
            return  # Allow empty UUIDs if not required
        
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, uuid_value.lower()):
            raise ValidationError(f"Invalid UUID format for field '{field}'", field=field, value=uuid_value)
    
    @staticmethod
    def validate_numeric_range(value: float, field: str, min_value: Optional[float] = None, max_value: Optional[float] = None) -> None:
        """
        Validate numeric value is within specified range.
        
        Args:
            value: Numeric value to validate
            field: Field name for error reporting
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Raises:
            ValidationError: If value is outside allowed range
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(f"Field '{field}' must be numeric", field=field, value=value)
        
        if min_value is not None and value < min_value:
            raise ValidationError(
                f"Field '{field}' must be at least {min_value}",
                field=field, value=value
            )
        
        if max_value is not None and value > max_value:
            raise ValidationError(
                f"Field '{field}' must be no more than {max_value}",
                field=field, value=value
            )
    
    @staticmethod
    def validate_date_format(date_value: str, field: str, date_format: str = "%Y-%m-%d") -> None:
        """
        Validate date string format.
        
        Args:
            date_value: Date string to validate
            field: Field name for error reporting
            date_format: Expected date format
            
        Raises:
            ValidationError: If date format is invalid
        """
        if not date_value:
            return  # Allow empty dates if not required
        
        try:
            datetime.strptime(date_value, date_format)
        except ValueError:
            raise ValidationError(
                f"Invalid date format for field '{field}'. Expected format: {date_format}",
                field=field, value=date_value
            )
    
    @staticmethod
    def validate_enum_value(value: Any, field: str, allowed_values: List[Any]) -> None:
        """
        Validate value is one of the allowed enum values.
        
        Args:
            value: Value to validate
            field: Field name for error reporting
            allowed_values: List of allowed values
            
        Raises:
            ValidationError: If value is not in allowed values
        """
        if value not in allowed_values:
            raise ValidationError(
                f"Field '{field}' must be one of: {', '.join(map(str, allowed_values))}",
                field=field, value=value
            )
    
    @staticmethod
    def validate_barcode(barcode: str, field: str = "barcode") -> None:
        """
        Validate barcode format.
        
        Args:
            barcode: Barcode string to validate
            field: Field name for error reporting
            
        Raises:
            ValidationError: If barcode format is invalid
        """
        if not barcode:
            return  # Allow empty barcodes if not required
        
        # Allow alphanumeric barcodes between 8 and 18 characters
        if not re.match(r'^[A-Za-z0-9]{8,18}$', barcode):
            raise ValidationError(
                f"Invalid barcode format for field '{field}'. Must be 8-18 alphanumeric characters",
                field=field, value=barcode
            )
    
    @staticmethod
    def validate_sku(sku: str, field: str = "sku") -> None:
        """
        Validate SKU format.
        
        Args:
            sku: SKU string to validate
            field: Field name for error reporting
            
        Raises:
            ValidationError: If SKU format is invalid
        """
        if not sku:
            return  # Allow empty SKUs if not required
        
        # SKU should be alphanumeric with optional hyphens/underscores, 3-20 characters
        if not re.match(r'^[A-Za-z0-9\-_]{3,20}$', sku):
            raise ValidationError(
                f"Invalid SKU format for field '{field}'. Must be 3-20 alphanumeric characters with optional hyphens/underscores",
                field=field, value=sku
            )


def validate_input(validator_class: type, method_name: str = "validate") -> Callable:
    """
    Decorator to validate input data using a validator class.
    
    Args:
        validator_class: Validator class to use
        method_name: Method name to call on validator instance
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Find the data parameter (usually first positional arg or 'data' keyword)
            data = None
            if args and isinstance(args[0], dict):
                data = args[0]
            elif 'data' in kwargs:
                data = kwargs['data']
            
            if data is not None:
                validator = validator_class()
                validate_method = getattr(validator, method_name)
                validate_method(data)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_required(required_fields: List[str]) -> Callable:
    """
    Decorator to validate required fields are present.
    
    Args:
        required_fields: List of required field names
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Find the data parameter
            data = None
            if args and isinstance(args[0], dict):
                data = args[0]
            elif 'data' in kwargs:
                data = kwargs['data']
            
            if data is not None:
                BaseValidator.validate_required_fields(data, required_fields)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
