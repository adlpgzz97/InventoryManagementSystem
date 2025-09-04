"""
Stock validation schemas and methods.
Validates stock item data according to business rules.
"""

from typing import Dict, Any
from datetime import date

from .base_validator import BaseValidator
from backend.exceptions import ValidationError


class StockValidator(BaseValidator):
    """Validator for stock item data."""
    
    # Stock field constraints
    REQUIRED_FIELDS = ['product_id', 'bin_id', 'on_hand']
    MAX_BATCH_ID_LENGTH = 100
    MAX_NOTES_LENGTH = 500
    
    def validate(self, data: Dict[str, Any]) -> None:
        """
        Validate stock item data.
        
        Args:
            data: Stock item data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields
        self.validate_required_fields(data, self.REQUIRED_FIELDS)
        
        # Validate individual fields
        if 'product_id' in data:
            self.validate_uuid(data['product_id'], 'product_id')
        
        if 'bin_id' in data:
            self.validate_uuid(data['bin_id'], 'bin_id')
        
        if 'on_hand' in data:
            self.validate_on_hand_quantity(data['on_hand'])
        
        if 'qty_reserved' in data:
            self.validate_reserved_quantity(data['qty_reserved'])
        
        if 'batch_id' in data:
            self.validate_batch_id(data['batch_id'])
        
        if 'expiry_date' in data:
            self.validate_expiry_date(data['expiry_date'])
        
        if 'received_date' in data:
            self.validate_received_date(data['received_date'])
    
    def validate_on_hand_quantity(self, quantity: Any) -> None:
        """Validate on-hand quantity."""
        if not isinstance(quantity, (int, float)):
            raise ValidationError("On-hand quantity must be numeric", field='on_hand', value=quantity)
        
        if quantity < 0:
            raise ValidationError("On-hand quantity cannot be negative", field='on_hand', value=quantity)
        
        # Check for reasonable maximum (1 million items)
        if quantity > 1000000:
            raise ValidationError("On-hand quantity exceeds maximum allowed (1,000,000)", field='on_hand', value=quantity)
    
    def validate_reserved_quantity(self, quantity: Any) -> None:
        """Validate reserved quantity."""
        if quantity is None:
            return  # Reserved quantity is optional
        
        if not isinstance(quantity, (int, float)):
            raise ValidationError("Reserved quantity must be numeric", field='qty_reserved', value=quantity)
        
        if quantity < 0:
            raise ValidationError("Reserved quantity cannot be negative", field='qty_reserved', value=quantity)
    
    def validate_batch_id(self, batch_id: str) -> None:
        """Validate batch ID."""
        if batch_id is None:
            return  # Batch ID is optional
        
        if not isinstance(batch_id, str):
            raise ValidationError("Batch ID must be a string", field='batch_id', value=batch_id)
        
        self.validate_string_length(batch_id, 'batch_id', min_length=1, max_length=self.MAX_BATCH_ID_LENGTH)
        
        # Check for invalid characters
        if any(char in batch_id for char in ['<', '>', '&', '"', "'"]):
            raise ValidationError("Batch ID contains invalid characters", field='batch_id', value=batch_id)
    
    def validate_expiry_date(self, expiry_date: Any) -> None:
        """Validate expiry date."""
        if expiry_date is None:
            return  # Expiry date is optional
        
        if isinstance(expiry_date, str):
            self.validate_date_format(expiry_date, 'expiry_date')
            expiry_date = date.fromisoformat(expiry_date)
        elif not isinstance(expiry_date, date):
            raise ValidationError("Expiry date must be a date or date string (YYYY-MM-DD)", field='expiry_date', value=expiry_date)
        
        # Check if expiry date is in the past
        if expiry_date < date.today():
            raise ValidationError("Expiry date cannot be in the past", field='expiry_date', value=expiry_date)
    
    def validate_received_date(self, received_date: Any) -> None:
        """Validate received date."""
        if received_date is None:
            return  # Received date is optional
        
        if isinstance(received_date, str):
            self.validate_date_format(received_date, 'received_date')
            received_date = date.fromisoformat(received_date)
        elif not isinstance(received_date, date):
            raise ValidationError("Received date must be a date or date string (YYYY-MM-DD)", field='received_date', value=received_date)
        
        # Check if received date is in the future
        if received_date > date.today():
            raise ValidationError("Received date cannot be in the future", field='received_date', value=received_date)
    
    def validate_stock_transaction(self, data: Dict[str, Any]) -> None:
        """
        Validate stock transaction data.
        
        Args:
            data: Stock transaction data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        required_fields = ['stock_item_id', 'transaction_type', 'quantity_change', 'user_id']
        self.validate_required_fields(data, required_fields)
        
        if 'stock_item_id' in data:
            self.validate_uuid(data['stock_item_id'], 'stock_item_id')
        
        if 'transaction_type' in data:
            self.validate_transaction_type(data['transaction_type'])
        
        if 'quantity_change' in data:
            self.validate_quantity_change(data['quantity_change'])
        
        if 'user_id' in data:
            self.validate_uuid(data['user_id'], 'user_id')
        
        if 'notes' in data:
            self.validate_notes(data['notes'])
    
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
    
    def validate_stock_transfer(self, data: Dict[str, Any]) -> None:
        """
        Validate stock transfer data.
        
        Args:
            data: Stock transfer data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        required_fields = ['stock_item_id', 'to_bin_id', 'quantity', 'user_id']
        self.validate_required_fields(data, required_fields)
        
        if 'stock_item_id' in data:
            self.validate_uuid(data['stock_item_id'], 'stock_item_id')
        
        if 'to_bin_id' in data:
            self.validate_uuid(data['to_bin_id'], 'to_bin_id')
        
        if 'quantity' in data:
            self.validate_transfer_quantity(data['quantity'])
        
        if 'user_id' in data:
            self.validate_uuid(data['user_id'], 'user_id')
        
        # Validate that source and destination are different
        if 'stock_item_id' in data and 'to_bin_id' in data:
            if data['stock_item_id'] == data['to_bin_id']:
                raise ValidationError("Source and destination must be different", field='to_bin_id', value=data['to_bin_id'])
    
    def validate_transfer_quantity(self, quantity: Any) -> None:
        """Validate transfer quantity."""
        if not isinstance(quantity, (int, float)):
            raise ValidationError("Transfer quantity must be numeric", field='quantity', value=quantity)
        
        if quantity <= 0:
            raise ValidationError("Transfer quantity must be positive", field='quantity', value=quantity)
        
        # Check for reasonable maximum
        if quantity > 100000:
            raise ValidationError("Transfer quantity exceeds maximum allowed (100,000)", field='quantity', value=quantity)
