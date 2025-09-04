"""
Transaction validation schemas and methods.
Validates transaction data according to business rules.
"""

from typing import Dict, Any
from datetime import datetime, date

from .base_validator import BaseValidator
from backend.exceptions import ValidationError


class TransactionValidator(BaseValidator):
    """Validator for transaction data."""
    
    # Transaction field constraints
    MAX_NOTES_LENGTH = 500
    MAX_REFERENCE_LENGTH = 100
    
    def validate(self, data: Dict[str, Any]) -> None:
        """
        Validate transaction data.
        
        Args:
            data: Transaction data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields
        required_fields = ['stock_item_id', 'transaction_type', 'quantity_change', 'quantity_before', 'quantity_after']
        self.validate_required_fields(data, required_fields)
        
        # Validate individual fields
        if 'stock_item_id' in data:
            self.validate_uuid(data['stock_item_id'], 'stock_item_id')
        
        if 'transaction_type' in data:
            self.validate_transaction_type(data['transaction_type'])
        
        if 'quantity_change' in data:
            self.validate_quantity_change(data['quantity_change'])
        
        if 'quantity_before' in data:
            self.validate_quantity_before(data['quantity_before'])
        
        if 'quantity_after' in data:
            self.validate_quantity_after(data['quantity_after'])
        
        if 'reference_id' in data:
            self.validate_reference_id(data['reference_id'])
        
        if 'notes' in data:
            self.validate_notes(data['notes'])
        
        if 'user_id' in data:
            self.validate_uuid(data['user_id'], 'user_id')
        
        # Validate quantity consistency
        self.validate_quantity_consistency(data)
    
    def validate_transaction_type(self, transaction_type: str) -> None:
        """Validate transaction type."""
        allowed_types = ['receive', 'ship', 'adjust', 'transfer', 'reserve', 'release']
        
        if not isinstance(transaction_type, str):
            raise ValidationError("Transaction type must be a string", field='transaction_type', value=transaction_type)
        
        if transaction_type.lower() not in allowed_types:
            raise ValidationError(
                f"Transaction type must be one of: {', '.join(allowed_types)}",
                field='transaction_type', value=transaction_type
            )
    
    def validate_quantity_change(self, quantity_change: Any) -> None:
        """Validate quantity change."""
        if not isinstance(quantity_change, (int, float)):
            raise ValidationError("Quantity change must be numeric", field='quantity_change', value=quantity_change)
        
        # Quantity change can be positive or negative
        if quantity_change == 0:
            raise ValidationError("Quantity change cannot be zero", field='quantity_change', value=quantity_change)
    
    def validate_quantity_before(self, quantity_before: Any) -> None:
        """Validate quantity before transaction."""
        if not isinstance(quantity_before, (int, float)):
            raise ValidationError("Quantity before must be numeric", field='quantity_before', value=quantity_before)
        
        if quantity_before < 0:
            raise ValidationError("Quantity before cannot be negative", field='quantity_before', value=quantity_before)
    
    def validate_quantity_after(self, quantity_after: Any) -> None:
        """Validate quantity after transaction."""
        if not isinstance(quantity_after, (int, float)):
            raise ValidationError("Quantity after must be numeric", field='quantity_after', value=quantity_after)
        
        if quantity_after < 0:
            raise ValidationError("Quantity after cannot be negative", field='quantity_after', value=quantity_after)
    
    def validate_reference_id(self, reference_id: str) -> None:
        """Validate reference ID."""
        if reference_id is None:
            return  # Reference ID is optional
        
        if not isinstance(reference_id, str):
            raise ValidationError("Reference ID must be a string", field='reference_id', value=reference_id)
        
        self.validate_string_length(reference_id, 'reference_id', min_length=1, max_length=self.MAX_REFERENCE_LENGTH)
        
        # Check for invalid characters
        if any(char in reference_id for char in ['<', '>', '&', '"', "'"]):
            raise ValidationError("Reference ID contains invalid characters", field='reference_id', value=reference_id)
    
    def validate_notes(self, notes: str) -> None:
        """Validate transaction notes."""
        if notes is None:
            return  # Notes are optional
        
        if not isinstance(notes, str):
            raise ValidationError("Notes must be a string", field='notes', value=notes)
        
        self.validate_string_length(notes, 'notes', min_length=0, max_length=self.MAX_NOTES_LENGTH)
        
        # Check for HTML tags
        if '<' in notes and '>' in notes:
            raise ValidationError("Notes cannot contain HTML tags", field='notes', value=notes)
    
    def validate_quantity_consistency(self, data: Dict[str, Any]) -> None:
        """
        Validate that quantity values are consistent.
        
        Args:
            data: Transaction data dictionary
            
        Raises:
            ValidationError: If quantities are inconsistent
        """
        if 'quantity_before' in data and 'quantity_change' in data and 'quantity_after' in data:
            quantity_before = data['quantity_before']
            quantity_change = data['quantity_change']
            quantity_after = data['quantity_after']
            
            # Check if quantity_after = quantity_before + quantity_change
            expected_after = quantity_before + quantity_change
            if abs(quantity_after - expected_after) > 0.001:  # Allow for floating point precision
                raise ValidationError(
                    f"Quantity after ({quantity_after}) must equal quantity before ({quantity_before}) + quantity change ({quantity_change})",
                    field='quantity_after', value=quantity_after
                )
    
    def validate_stock_transfer(self, data: Dict[str, Any]) -> None:
        """
        Validate stock transfer transaction.
        
        Args:
            data: Stock transfer data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        required_fields = ['from_stock_item_id', 'to_stock_item_id', 'quantity', 'user_id']
        self.validate_required_fields(data, required_fields)
        
        if 'from_stock_item_id' in data:
            self.validate_uuid(data['from_stock_item_id'], 'from_stock_item_id')
        
        if 'to_stock_item_id' in data:
            self.validate_uuid(data['to_stock_item_id'], 'to_stock_item_id')
        
        if 'quantity' in data:
            self.validate_transfer_quantity(data['quantity'])
        
        if 'user_id' in data:
            self.validate_uuid(data['user_id'], 'user_id')
        
        # Validate that source and destination are different
        if 'from_stock_item_id' in data and 'to_stock_item_id' in data:
            if data['from_stock_item_id'] == data['to_stock_item_id']:
                raise ValidationError(
                    "Source and destination stock items must be different",
                    field='to_stock_item_id', value=data['to_stock_item_id']
                )
    
    def validate_transfer_quantity(self, quantity: Any) -> None:
        """Validate transfer quantity."""
        if not isinstance(quantity, (int, float)):
            raise ValidationError("Transfer quantity must be numeric", field='quantity', value=quantity)
        
        if quantity <= 0:
            raise ValidationError("Transfer quantity must be positive", field='quantity', value=quantity)
        
        # Check for reasonable maximum
        if quantity > 100000:
            raise ValidationError("Transfer quantity exceeds maximum allowed (100,000)", field='quantity', value=quantity)
    
    def validate_adjustment_transaction(self, data: Dict[str, Any]) -> None:
        """
        Validate stock adjustment transaction.
        
        Args:
            data: Stock adjustment data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        required_fields = ['stock_item_id', 'adjustment_reason', 'quantity_change', 'user_id']
        self.validate_required_fields(data, required_fields)
        
        if 'stock_item_id' in data:
            self.validate_uuid(data['stock_item_id'], 'stock_item_id')
        
        if 'adjustment_reason' in data:
            self.validate_adjustment_reason(data['adjustment_reason'])
        
        if 'quantity_change' in data:
            self.validate_quantity_change(data['quantity_change'])
        
        if 'user_id' in data:
            self.validate_uuid(data['user_id'], 'user_id')
    
    def validate_adjustment_reason(self, reason: str) -> None:
        """Validate adjustment reason."""
        if not isinstance(reason, str):
            raise ValidationError("Adjustment reason must be a string", field='adjustment_reason', value=reason)
        
        self.validate_string_length(reason, 'adjustment_reason', min_length=1, max_length=200)
        
        # Check for invalid characters
        if any(char in reason for char in ['<', '>', '&', '"', "'"]):
            raise ValidationError("Adjustment reason contains invalid characters", field='adjustment_reason', value=reason)
