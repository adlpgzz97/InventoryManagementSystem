"""
Warehouse validation schemas and methods.
Validates warehouse data according to business rules.
"""

from typing import Dict, Any
import re

from .base_validator import BaseValidator
from backend.exceptions import ValidationError


class WarehouseValidator(BaseValidator):
    """Validator for warehouse data."""
    
    # Warehouse field constraints
    REQUIRED_FIELDS = ['name']
    MAX_NAME_LENGTH = 255
    MAX_ADDRESS_LENGTH = 500
    MAX_CODE_LENGTH = 20
    
    def validate(self, data: Dict[str, Any]) -> None:
        """
        Validate warehouse data.
        
        Args:
            data: Warehouse data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields
        self.validate_required_fields(data, self.REQUIRED_FIELDS)
        
        # Validate individual fields
        if 'name' in data:
            self.validate_name(data['name'])
        
        if 'address' in data:
            self.validate_address(data['address'])
        
        if 'code' in data:
            self.validate_code(data['code'])
    
    def validate_name(self, name: str) -> None:
        """Validate warehouse name."""
        self.validate_string_length(name, 'name', min_length=1, max_length=self.MAX_NAME_LENGTH)
        
        # Check for invalid characters
        if any(char in name for char in ['<', '>', '&', '"', "'"]):
            raise ValidationError("Warehouse name contains invalid characters", field='name', value=name)
    
    def validate_address(self, address: str) -> None:
        """Validate warehouse address."""
        if address is None:
            return  # Address is optional
        
        self.validate_string_length(address, 'address', min_length=0, max_length=self.MAX_ADDRESS_LENGTH)
        
        # Check for HTML tags
        if '<' in address and '>' in address:
            raise ValidationError("Address cannot contain HTML tags", field='address', value=address)
    
    def validate_code(self, code: str) -> None:
        """Validate warehouse code."""
        if code is None:
            return  # Code is optional
        
        self.validate_string_length(code, 'code', min_length=1, max_length=self.MAX_CODE_LENGTH)
        
        # Check for valid warehouse code format (alphanumeric with optional hyphens)
        if not re.match(r'^[A-Za-z0-9\-]+$', code):
            raise ValidationError(
                "Warehouse code must contain only letters, numbers, and hyphens",
                field='code', value=code
            )
    
    def validate_location_data(self, data: Dict[str, Any]) -> None:
        """
        Validate warehouse location data.
        
        Args:
            data: Location data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        required_fields = ['warehouse_id', 'full_code']
        self.validate_required_fields(data, required_fields)
        
        if 'warehouse_id' in data:
            self.validate_uuid(data['warehouse_id'], 'warehouse_id')
        
        if 'full_code' in data:
            self.validate_location_code(data['full_code'])
    
    def validate_location_code(self, code: str) -> None:
        """Validate location code format."""
        if not isinstance(code, str):
            raise ValidationError("Location code must be a string", field='full_code', value=code)
        
        # Location code should follow pattern like "A1-B2-C3" or "A1B2C3"
        if not re.match(r'^[A-Za-z0-9\-]+$', code):
            raise ValidationError(
                "Location code must contain only letters, numbers, and hyphens",
                field='full_code', value=code
            )
    
    def validate_bin_data(self, data: Dict[str, Any]) -> None:
        """
        Validate bin data.
        
        Args:
            data: Bin data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        required_fields = ['code', 'location_id']
        self.validate_required_fields(data, required_fields)
        
        if 'code' in data:
            self.validate_bin_code(data['code'])
        
        if 'location_id' in data:
            self.validate_uuid(data['location_id'], 'location_id')
    
    def validate_bin_code(self, code: str) -> None:
        """Validate bin code format."""
        if not isinstance(code, str):
            raise ValidationError("Bin code must be a string", field='code', value=code)
        
        # Bin code should follow pattern like "B001", "B002", etc.
        if not re.match(r'^B[0-9]+$', code):
            raise ValidationError(
                "Bin code must follow pattern 'B' followed by numbers (e.g., B001, B002)",
                field='code', value=code
            )
