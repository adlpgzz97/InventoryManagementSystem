"""
Product validation schemas and methods.
Validates product data according to business rules.
"""

from typing import Dict, Any, List
import re

from .base_validator import BaseValidator
from backend.exceptions import ValidationError


class ProductValidator(BaseValidator):
    """Validator for product data."""
    
    # Product field constraints
    REQUIRED_FIELDS = ['name', 'sku']
    MAX_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 1000
    MAX_DIMENSIONS_LENGTH = 100
    MAX_WEIGHT = 10000.0  # 10 tons max
    MIN_WEIGHT = 0.001    # 1 gram min
    
    def validate(self, data: Dict[str, Any]) -> None:
        """
        Validate product data.
        
        Args:
            data: Product data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields
        self.validate_required_fields(data, self.REQUIRED_FIELDS)
        
        # Validate individual fields
        if 'name' in data:
            self.validate_name(data['name'])
        
        if 'sku' in data:
            self.validate_sku(data['sku'])
        
        if 'description' in data:
            self.validate_description(data['description'])
        
        if 'dimensions' in data:
            self.validate_dimensions(data['dimensions'])
        
        if 'weight' in data:
            self.validate_weight(data['weight'])
        
        if 'barcode' in data:
            self.validate_barcode(data['barcode'])
        
        if 'picture_url' in data:
            self.validate_picture_url(data['picture_url'])
    
    def validate_name(self, name: str) -> None:
        """Validate product name."""
        self.validate_string_length(name, 'name', min_length=1, max_length=self.MAX_NAME_LENGTH)
        
        # Check for invalid characters
        if any(char in name for char in ['<', '>', '&', '"', "'"]):
            raise ValidationError("Product name contains invalid characters", field='name', value=name)
    
    def validate_sku(self, sku: str) -> None:
        """Validate product SKU."""
        self.validate_sku(sku, 'sku')
        
        # Check for reserved SKU patterns
        reserved_patterns = ['TEST', 'DEMO', 'SAMPLE', 'TEMP']
        if any(pattern in sku.upper() for pattern in reserved_patterns):
            raise ValidationError(
                f"SKU cannot contain reserved patterns: {', '.join(reserved_patterns)}",
                field='sku', value=sku
            )
    
    def validate_description(self, description: str) -> None:
        """Validate product description."""
        if description is None:
            return  # Description is optional
        
        self.validate_string_length(description, 'description', min_length=0, max_length=self.MAX_DESCRIPTION_LENGTH)
        
        # Check for HTML tags
        if '<' in description and '>' in description:
            raise ValidationError("Description cannot contain HTML tags", field='description', value=description)
    
    def validate_dimensions(self, dimensions: str) -> None:
        """Validate product dimensions."""
        if dimensions is None:
            return  # Dimensions are optional
        
        self.validate_string_length(dimensions, 'dimensions', min_length=0, max_length=self.MAX_DIMENSIONS_LENGTH)
        
        # Check for valid dimension format (e.g., "10x5x2 cm", "L:10 W:5 H:2")
        dimension_patterns = [
            r'^\d+(\.\d+)?x\d+(\.\d+)?x\d+(\.\d+)?\s*[a-zA-Z]+$',  # 10x5x2 cm
            r'^[LWH]:\d+(\.\d+)?\s*[a-zA-Z]+$',  # L:10 W:5 H:2 cm
            r'^\d+(\.\d+)?\s*[a-zA-Z]+\s*x\s*\d+(\.\d+)?\s*[a-zA-Z]+\s*x\s*\d+(\.\d+)?\s*[a-zA-Z]+$'  # 10 cm x 5 cm x 2 cm
        ]
        
        if not any(re.match(pattern, dimensions) for pattern in dimension_patterns):
            raise ValidationError(
                "Invalid dimensions format. Use format like '10x5x2 cm' or 'L:10 W:5 H:2 cm'",
                field='dimensions', value=dimensions
            )
    
    def validate_weight(self, weight: Any) -> None:
        """Validate product weight."""
        if weight is None:
            return  # Weight is optional
        
        if not isinstance(weight, (int, float)):
            raise ValidationError("Weight must be numeric", field='weight', value=weight)
        
        self.validate_numeric_range(weight, 'weight', min_value=self.MIN_WEIGHT, max_value=self.MAX_WEIGHT)
    
    def validate_picture_url(self, url: str) -> None:
        """Validate product picture URL."""
        if url is None:
            return  # Picture URL is optional
        
        if not isinstance(url, str):
            raise ValidationError("Picture URL must be a string", field='picture_url', value=url)
        
        # Basic URL validation
        url_patterns = [
            r'^https?://[^\s/$.?#].[^\s]*$',  # HTTP/HTTPS URLs
            r'^data:image/[^;]+;base64,[A-Za-z0-9+/=]+$',  # Data URLs
            r'^/[^\s]*$'  # Relative URLs
        ]
        
        if not any(re.match(pattern, url) for pattern in url_patterns):
            raise ValidationError("Invalid picture URL format", field='picture_url', value=url)
    
    def validate_batch_tracking(self, batch_tracked: Any) -> None:
        """Validate batch tracking flag."""
        if batch_tracked is not None and not isinstance(batch_tracked, bool):
            raise ValidationError("Batch tracking must be a boolean value", field='batch_tracked', value=batch_tracked)
    
    def validate_for_creation(self, data: Dict[str, Any]) -> None:
        """
        Validate product data for creation (stricter validation).
        
        Args:
            data: Product data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        # Basic validation
        self.validate(data)
        
        # Additional creation-specific validations
        if 'sku' in data:
            # Check SKU uniqueness (this would typically check against database)
            # For now, just validate format
            pass
    
    def validate_for_update(self, data: Dict[str, Any]) -> None:
        """
        Validate product data for updates.
        
        Args:
            data: Product data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        # For updates, we only validate fields that are present
        if 'name' in data:
            self.validate_name(data['name'])
        
        if 'sku' in data:
            self.validate_sku(data['sku'])
        
        if 'description' in data:
            self.validate_description(data['description'])
        
        if 'dimensions' in data:
            self.validate_dimensions(data['dimensions'])
        
        if 'weight' in data:
            self.validate_weight(data['weight'])
        
        if 'barcode' in data:
            self.validate_barcode(data['barcode'])
        
        if 'picture_url' in data:
            self.validate_picture_url(data['picture_url'])
        
        if 'batch_tracked' in data:
            self.validate_batch_tracking(data['batch_tracked'])
    
    def validate_search_criteria(self, criteria: Dict[str, Any]) -> None:
        """
        Validate product search criteria.
        
        Args:
            criteria: Search criteria dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        allowed_fields = ['name', 'sku', 'barcode', 'category', 'supplier']
        
        for field in criteria:
            if field not in allowed_fields:
                raise ValidationError(f"Invalid search field: {field}", field=field)
            
            value = criteria[field]
            if value is not None and not isinstance(value, str):
                raise ValidationError(f"Search value for {field} must be a string", field=field, value=value)
            
            if isinstance(value, str) and len(value.strip()) == 0:
                raise ValidationError(f"Search value for {field} cannot be empty", field=field, value=value)
