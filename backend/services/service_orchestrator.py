"""
Service Orchestrator for Inventory Management System
Coordinates complex operations across multiple services
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from backend.services.base_service import BaseService, ServiceError, ValidationError, NotFoundError
from backend.services.warehouse_service import WarehouseService
from backend.services.product_service import ProductService
from backend.services.stock_service import StockService
from backend.services.transaction_service import TransactionService
from backend.services.scanner_service import ScannerService

logger = logging.getLogger(__name__)


class ServiceOrchestrator(BaseService):
    """Orchestrates complex operations across multiple services"""
    
    def __init__(self):
        super().__init__()
        self.warehouse_service = WarehouseService()
        self.product_service = ProductService()
        self.stock_service = StockService()
        self.transaction_service = TransactionService()
        self.scanner_service = ScannerService()
    
    def perform_stock_transfer(self, source_bin_id: str, target_bin_id: str, 
                             product_id: str, quantity: int, user_id: str, 
                             notes: str = '') -> Dict[str, Any]:
        """Perform a stock transfer between bins"""
        try:
            self.log_operation("perform_stock_transfer", {
                "source_bin_id": source_bin_id, "target_bin_id": target_bin_id,
                "product_id": product_id, "quantity": quantity, "user_id": user_id
            })
            
            # Validate required fields
            self.validate_required_fields({
                "source_bin_id": source_bin_id, "target_bin_id": target_bin_id,
                "product_id": product_id, "quantity": quantity, "user_id": user_id
            })
            
            # Validate quantity
            if quantity <= 0:
                raise ValidationError("Transfer quantity must be positive")
            
            # Get source stock item
            source_stock = self.stock_service.get_stock_by_bin_and_product(source_bin_id, product_id)
            if not source_stock:
                raise NotFoundError(f"No stock found for product {product_id} in source bin {source_bin_id}")
            
            if source_stock['on_hand'] < quantity:
                raise ValidationError(f"Insufficient stock. Available: {source_stock['on_hand']}, Requested: {quantity}")
            
            # Check if target bin can accommodate the transfer
            target_bin = self.warehouse_service.get_bin_stock(target_bin_id)
            target_capacity = self._calculate_bin_capacity(target_bin_id)
            target_used = sum(item['quantity'] for item in target_bin)
            
            if target_used + quantity > target_capacity:
                raise ValidationError(f"Target bin capacity exceeded. Available: {target_capacity - target_used}, Requested: {quantity}")
            
            # Create transfer transaction (outbound from source)
            outbound_transaction = self.transaction_service.create_transaction(
                stock_item_id=source_stock['id'],
                transaction_type='transfer',
                quantity_change=-quantity,
                user_id=user_id,
                notes=f"Transfer out to bin {target_bin_id}: {notes}"
            )
            
            # Create transfer transaction (inbound to target)
            # First check if stock item exists in target bin
            target_stock = self.stock_service.get_stock_by_bin_and_product(target_bin_id, product_id)
            
            if target_stock:
                # Update existing stock item
                inbound_transaction = self.transaction_service.create_transaction(
                    stock_item_id=target_stock['id'],
                    transaction_type='transfer',
                    quantity_change=quantity,
                    user_id=user_id,
                    notes=f"Transfer in from bin {source_bin_id}: {notes}"
                )
            else:
                # Create new stock item in target bin
                target_stock_item = self.stock_service.create_stock_item(
                    product_id=product_id,
                    bin_id=target_bin_id,
                    on_hand=quantity,
                    qty_reserved=0
                )
                
                inbound_transaction = self.transaction_service.create_transaction(
                    stock_item_id=target_stock_item['id'],
                    transaction_type='transfer',
                    quantity_change=quantity,
                    user_id=user_id,
                    notes=f"Transfer in from bin {source_bin_id}: {notes}"
                )
            
            return {
                'success': True,
                'transfer_id': f"TRF-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                'source_bin_id': source_bin_id,
                'target_bin_id': target_bin_id,
                'product_id': product_id,
                'quantity': quantity,
                'outbound_transaction': outbound_transaction,
                'inbound_transaction': inbound_transaction,
                'timestamp': datetime.now().isoformat()
            }
            
        except (ValidationError, NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.log_error("perform_stock_transfer", e)
            raise ServiceError(f"Failed to perform stock transfer: {str(e)}")
    
    def perform_cycle_count(self, bin_id: str, product_id: str, counted_quantity: int, 
                           user_id: str, notes: str = '') -> Dict[str, Any]:
        """Perform a cycle count adjustment"""
        try:
            self.log_operation("perform_cycle_count", {
                "bin_id": bin_id, "product_id": product_id, 
                "counted_quantity": counted_quantity, "user_id": user_id
            })
            
            # Validate required fields
            self.validate_required_fields({
                "bin_id": bin_id, "product_id": product_id, 
                "counted_quantity": counted_quantity, "user_id": user_id
            })
            
            # Validate quantity
            if counted_quantity < 0:
                raise ValidationError("Counted quantity cannot be negative")
            
            # Get current stock
            current_stock = self.stock_service.get_stock_by_bin_and_product(bin_id, product_id)
            if not current_stock:
                raise NotFoundError(f"No stock found for product {product_id} in bin {bin_id}")
            
            # Calculate adjustment
            quantity_adjustment = counted_quantity - current_stock['on_hand']
            
            if quantity_adjustment == 0:
                return {
                    'success': True,
                    'message': 'Count matches system quantity - no adjustment needed',
                    'current_quantity': current_stock['on_hand'],
                    'counted_quantity': counted_quantity,
                    'adjustment': 0
                }
            
            # Create cycle count transaction
            transaction = self.transaction_service.create_transaction(
                stock_item_id=current_stock['id'],
                transaction_type='cycle_count',
                quantity_change=quantity_adjustment,
                user_id=user_id,
                notes=f"Cycle count adjustment: {notes}"
            )
            
            return {
                'success': True,
                'current_quantity': current_stock['on_hand'],
                'counted_quantity': counted_quantity,
                'adjustment': quantity_adjustment,
                'transaction': transaction
            }
            
        except (ValidationError, NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.log_error("perform_cycle_count", e)
            raise ServiceError(f"Failed to perform cycle count: {str(e)}")
    
    def perform_bulk_receipt(self, warehouse_id: str, receipt_data: List[Dict[str, Any]], 
                            user_id: str, reference_id: str = '') -> Dict[str, Any]:
        """Perform bulk receipt of multiple products"""
        try:
            self.log_operation("perform_bulk_receipt", {
                "warehouse_id": warehouse_id, "receipt_count": len(receipt_data), 
                "user_id": user_id, "reference_id": reference_id
            })
            
            # Validate required fields
            self.validate_required_fields({
                "warehouse_id": warehouse_id, "receipt_data": receipt_data, "user_id": user_id
            })
            
            # Validate warehouse exists
            warehouse = self.warehouse_service.get_warehouse_by_id(warehouse_id)
            
            # Process each receipt item
            results = []
            errors = []
            
            for item in receipt_data:
                try:
                    # Validate item data
                    required_fields = ['product_id', 'bin_id', 'quantity']
                    for field in required_fields:
                        if field not in item:
                            errors.append(f"Missing required field '{field}' in item {item}")
                            continue
                    
                    # Validate bin belongs to warehouse
                    bin_stock = self.warehouse_service.get_bin_stock(item['bin_id'])
                    if not bin_stock:
                        errors.append(f"Bin {item['bin_id']} not found")
                        continue
                    
                    # Check bin capacity
                    bin_capacity = self._calculate_bin_capacity(item['bin_id'])
                    current_used = sum(stock['quantity'] for stock in bin_stock)
                    
                    if current_used + item['quantity'] > bin_capacity:
                        errors.append(f"Bin {item['bin_id']} capacity exceeded for product {item['product_id']}")
                        continue
                    
                    # Create or update stock item
                    existing_stock = self.stock_service.get_stock_by_bin_and_product(
                        item['bin_id'], item['product_id']
                    )
                    
                    if existing_stock:
                        # Update existing stock
                        transaction = self.transaction_service.create_transaction(
                            stock_item_id=existing_stock['id'],
                            transaction_type='receive',
                            quantity_change=item['quantity'],
                            user_id=user_id,
                            notes=f"Bulk receipt - {reference_id}",
                            reference_id=reference_id
                        )
                    else:
                        # Create new stock item
                        stock_item = self.stock_service.create_stock_item(
                            product_id=item['product_id'],
                            bin_id=item['bin_id'],
                            on_hand=item['quantity'],
                            qty_reserved=0
                        )
                        
                        transaction = self.transaction_service.create_transaction(
                            stock_item_id=stock_item['id'],
                            transaction_type='receive',
                            quantity_change=item['quantity'],
                            user_id=user_id,
                            notes=f"Bulk receipt - {reference_id}",
                            reference_id=reference_id
                        )
                    
                    results.append({
                        'product_id': item['product_id'],
                        'bin_id': item['bin_id'],
                        'quantity': item['quantity'],
                        'success': True,
                        'transaction_id': transaction['id']
                    })
                    
                except Exception as e:
                    errors.append(f"Failed to process item {item}: {str(e)}")
                    continue
            
            return {
                'success': len(errors) == 0,
                'total_items': len(receipt_data),
                'successful_items': len(results),
                'failed_items': len(errors),
                'results': results,
                'errors': errors,
                'reference_id': reference_id
            }
            
        except (ValidationError, NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.log_error("perform_bulk_receipt", e)
            raise ServiceError(f"Failed to perform bulk receipt: {str(e)}")
    
    def get_inventory_summary(self, warehouse_id: str = None) -> Dict[str, Any]:
        """Get comprehensive inventory summary"""
        try:
            self.log_operation("get_inventory_summary", {"warehouse_id": warehouse_id})
            
            # Get warehouse statistics
            warehouse_stats = self.warehouse_service.get_warehouse_statistics()
            
            # Get product statistics
            product_stats = self.product_service.get_product_statistics()
            
            # Get transaction statistics
            transaction_stats = self.transaction_service.get_transaction_statistics()
            
            # Get scanner statistics
            scanner_stats = self.scanner_service.get_scanner_statistics()
            
            # Calculate overall metrics
            total_value = self._calculate_total_inventory_value(warehouse_id)
            
            return {
                'warehouse_summary': warehouse_stats,
                'product_summary': product_stats,
                'transaction_summary': transaction_stats,
                'scanner_summary': scanner_stats,
                'overall_metrics': {
                    'total_inventory_value': total_value,
                    'total_warehouses': warehouse_stats['total_warehouses'],
                    'total_products': product_stats['total_products'],
                    'total_transactions': transaction_stats['summary']['total_transactions'],
                    'barcode_coverage': scanner_stats['barcode_coverage_percentage']
                }
            }
            
        except Exception as e:
            self.log_error("get_inventory_summary", e)
            raise ServiceError(f"Failed to get inventory summary: {str(e)}")
    
    def _calculate_bin_capacity(self, bin_id: str) -> int:
        """Calculate bin capacity (placeholder for future implementation)"""
        # This would typically query bin configuration or use default values
        # For now, return a reasonable default
        return 1000
    
    def _calculate_total_inventory_value(self, warehouse_id: str = None) -> float:
        """Calculate total inventory value (placeholder for future implementation)"""
        # This would typically query product costs and multiply by quantities
        # For now, return a placeholder value
        return 0.0
    
    def rollback_operation(self, operation_id: str, user_id: str, reason: str = '') -> Dict[str, Any]:
        """Rollback a complex operation"""
        try:
            self.log_operation("rollback_operation", {
                "operation_id": operation_id, "user_id": user_id, "reason": reason
            })
            
            # Validate required fields
            self.validate_required_fields({
                "operation_id": operation_id, "user_id": user_id
            })
            
            # Get operation audit trail
            audit_trail = self.transaction_service.get_transaction_audit_trail(operation_id)
            
            if not audit_trail:
                raise NotFoundError(f"No audit trail found for operation {operation_id}")
            
            # Reverse transactions in reverse order
            reversed_transactions = []
            for transaction in reversed(audit_trail):
                try:
                    reversed_transaction = self.transaction_service.reverse_transaction(
                        transaction_id=transaction['id'],
                        user_id=user_id,
                        notes=f"Rollback of operation {operation_id}: {reason}"
                    )
                    reversed_transactions.append(reversed_transaction)
                except Exception as e:
                    # Log error but continue with other transactions
                    self.log_error(f"Failed to reverse transaction {transaction['id']}", e)
                    continue
            
            return {
                'success': True,
                'operation_id': operation_id,
                'original_transactions': len(audit_trail),
                'reversed_transactions': len(reversed_transactions),
                'reversed_transaction_ids': [t['id'] for t in reversed_transactions],
                'rollback_reason': reason,
                'timestamp': datetime.now().isoformat()
            }
            
        except (ValidationError, NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.log_error("rollback_operation", e)
            raise ServiceError(f"Failed to rollback operation: {str(e)}")
