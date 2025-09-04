"""
Transaction Service for Inventory Management System
Handles stock transaction business logic
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from backend.services.base_service import BaseService, ServiceError, ValidationError, NotFoundError
from backend.models.stock import StockTransaction, StockItem
from backend.models.product import Product
from backend.models.warehouse import Warehouse, Location, Bin
from backend.models.user import User
from backend.repositories.transaction_repository import TransactionRepository
from backend.utils.database import execute_query

logger = logging.getLogger(__name__)


class TransactionService(BaseService):
    """Service for stock transaction operations"""
    
    def __init__(self):
        super().__init__()
        self.transaction_repository = TransactionRepository()
    
    def get_all_transactions(self, page: int = 1, per_page: int = 25, 
                           transaction_type: str = '', product_id: str = '', 
                           warehouse_id: str = '', date_from: str = '', 
                           date_to: str = '') -> Dict[str, Any]:
        """Get all transactions with filtering and pagination"""
        try:
            self.log_operation("get_all_transactions", {
                "page": page, "per_page": per_page, "transaction_type": transaction_type,
                "product_id": product_id, "warehouse_id": warehouse_id,
                "date_from": date_from, "date_to": date_to
            })
            
            # Build WHERE clause
            where_conditions = []
            params = []
            
            if transaction_type:
                where_conditions.append("st.transaction_type = %s")
                params.append(transaction_type)
            
            if product_id:
                where_conditions.append("si.product_id = %s")
                params.append(product_id)
            
            if warehouse_id:
                where_conditions.append("l.warehouse_id = %s")
                params.append(warehouse_id)
            
            if date_from:
                where_conditions.append("st.created_at >= %s")
                params.append(date_from)
            
            if date_to:
                where_conditions.append("st.created_at <= %s")
                params.append(date_to)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Count total transactions
            count_query = f"""
                SELECT COUNT(*) as total
                FROM stock_transactions st
                LEFT JOIN stock_items si ON st.stock_item_id = si.id
                LEFT JOIN bins b ON si.bin_id = b.id
                LEFT JOIN locations l ON b.location_id = l.id
                WHERE {where_clause}
            """
            
            total_count = execute_query(count_query, params, fetch_one=True)
            total_transactions = total_count['total'] if total_count else 0
            
            # Calculate pagination
            offset = (page - 1) * per_page
            total_pages = (total_transactions + per_page - 1) // per_page
            
            # Get transactions with pagination
            query = f"""
                SELECT 
                    st.id,
                    st.transaction_type,
                    st.quantity_change,
                    st.quantity_before,
                    st.quantity_after,
                    st.notes,
                    st.created_at,
                    st.reference_id,
                    p.sku,
                    p.name as product_name,
                    b.code as bin_code,
                    w.name as warehouse_name,
                    l.full_code,
                    u.username as user_name
                FROM stock_transactions st
                LEFT JOIN stock_items si ON st.stock_item_id = si.id
                LEFT JOIN products p ON si.product_id = p.id
                LEFT JOIN bins b ON si.bin_id = b.id
                LEFT JOIN locations l ON b.location_id = l.id
                LEFT JOIN warehouses w ON l.warehouse_id = w.id
                LEFT JOIN users u ON st.user_id = u.id
                WHERE {where_clause}
                ORDER BY st.created_at DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([per_page, offset])
            transactions = execute_query(query, params, fetch_all=True)
            
            return {
                "transactions": transactions,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_transactions,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
            
        except Exception as e:
            self.log_error("get_all_transactions", e)
            raise ServiceError(f"Failed to retrieve transactions: {str(e)}")
    
    def get_transaction_by_id(self, transaction_id: str) -> Dict[str, Any]:
        """Get transaction by ID"""
        try:
            self.log_operation("get_transaction_by_id", {"transaction_id": transaction_id})
            
            # Validate required fields
            self.validate_required_fields({"transaction_id": transaction_id})
            
            query = """
                SELECT 
                    st.*,
                    p.sku,
                    p.name as product_name,
                    b.code as bin_code,
                    w.name as warehouse_name,
                    l.full_code,
                    u.username as user_name
                FROM stock_transactions st
                LEFT JOIN stock_items si ON st.stock_item_id = si.id
                LEFT JOIN products p ON si.product_id = p.id
                LEFT JOIN bins b ON si.bin_id = b.id
                LEFT JOIN locations l ON b.location_id = l.id
                LEFT JOIN warehouses w ON l.warehouse_id = w.id
                LEFT JOIN users u ON st.user_id = u.id
                WHERE st.id = %s
            """
            
            transaction = execute_query(query, [transaction_id], fetch_one=True)
            if not transaction:
                raise NotFoundError(f"Transaction with ID {transaction_id} not found")
            
            return transaction
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.log_error("get_transaction_by_id", e)
            raise ServiceError(f"Failed to retrieve transaction: {str(e)}")
    
    def create_transaction(self, stock_item_id: str, transaction_type: str, 
                          quantity_change: int, user_id: str, notes: str = '', 
                          reference_id: str = '') -> Dict[str, Any]:
        """Create a new stock transaction"""
        try:
            self.log_operation("create_transaction", {
                "stock_item_id": stock_item_id, "transaction_type": transaction_type,
                "quantity_change": quantity_change, "user_id": user_id,
                "notes": notes, "reference_id": reference_id
            })
            
            # Validate required fields
            self.validate_required_fields({
                "stock_item_id": stock_item_id,
                "transaction_type": transaction_type,
                "quantity_change": quantity_change,
                "user_id": user_id
            })
            
            # Validate transaction type
            valid_types = ['receive', 'ship', 'adjust', 'transfer', 'cycle_count']
            if transaction_type not in valid_types:
                raise ValidationError(f"Invalid transaction type. Must be one of: {', '.join(valid_types)}")
            
            # Validate quantity change
            if quantity_change == 0:
                raise ValidationError("Quantity change cannot be zero")
            
            # Get stock item
            stock_item = StockItem.get_by_id(stock_item_id)
            if not stock_item:
                raise NotFoundError(f"Stock item with ID {stock_item_id} not found")
            
            # Get current quantity
            quantity_before = stock_item.on_hand
            quantity_after = quantity_before + quantity_change
            
            # Validate quantity after transaction
            if quantity_after < 0:
                raise ValidationError(f"Transaction would result in negative stock. Current: {quantity_before}, Change: {quantity_change}")
            
            # Sanitize inputs
            notes = self.sanitize_input(notes)
            reference_id = self.sanitize_input(reference_id)
            
            # Create transaction
            transaction = StockTransaction.create(
                stock_item_id=stock_item_id,
                transaction_type=transaction_type,
                quantity_change=quantity_change,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                user_id=user_id,
                notes=notes,
                reference_id=reference_id
            )
            
            if not transaction:
                raise ServiceError("Failed to create transaction")
            
            # Update stock item quantity
            stock_item.update(on_hand=quantity_after)
            
            return transaction.to_dict()
            
        except (ValidationError, NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.log_error("create_transaction", e)
            raise ServiceError(f"Failed to create transaction: {str(e)}")
    
    def get_transaction_statistics(self, date_from: str = '', date_to: str = '') -> Dict[str, Any]:
        """Get transaction statistics"""
        try:
            self.log_operation("get_transaction_statistics", {"date_from": date_from, "date_to": date_to})
            
            # Build WHERE clause for date filtering
            where_conditions = []
            params = []
            
            if date_from:
                where_conditions.append("st.created_at >= %s")
                params.append(date_from)
            
            if date_to:
                where_conditions.append("st.created_at <= %s")
                params.append(date_to)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Get statistics
            stats_query = f"""
                SELECT 
                    COUNT(*) as total_transactions,
                    COUNT(DISTINCT st.stock_item_id) as unique_stock_items,
                    COUNT(DISTINCT p.id) as unique_products,
                    SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) as total_received,
                    SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END) as total_shipped,
                    SUM(CASE WHEN st.transaction_type = 'adjust' THEN st.quantity_change ELSE 0 END) as total_adjusted,
                    SUM(CASE WHEN st.transaction_type = 'transfer' THEN ABS(st.quantity_change) ELSE 0 END) as total_transferred,
                    SUM(CASE WHEN st.transaction_type = 'cycle_count' THEN ABS(st.quantity_change) ELSE 0 END) as total_cycle_counted
                FROM stock_transactions st
                LEFT JOIN stock_items si ON st.stock_item_id = si.id
                LEFT JOIN products p ON si.product_id = p.id
                WHERE {where_clause}
            """
            
            stats = execute_query(stats_query, params, fetch_one=True)
            
            # Get transaction type breakdown
            type_query = f"""
                SELECT 
                    st.transaction_type,
                    COUNT(*) as count,
                    SUM(ABS(st.quantity_change)) as total_quantity
                FROM stock_transactions st
                WHERE {where_clause}
                GROUP BY st.transaction_type
                ORDER BY count DESC
            """
            
            type_breakdown = execute_query(type_query, params, fetch_all=True)
            
            # Get daily transaction trend
            trend_query = f"""
                SELECT 
                    DATE(st.created_at) as date,
                    COUNT(*) as transaction_count,
                    SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) as received,
                    SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END) as shipped
                FROM stock_transactions st
                WHERE {where_clause}
                GROUP BY DATE(st.created_at)
                ORDER BY date DESC
                LIMIT 30
            """
            
            daily_trend = execute_query(trend_query, params, fetch_all=True)
            
            return {
                "summary": stats,
                "type_breakdown": type_breakdown,
                "daily_trend": daily_trend
            }
            
        except Exception as e:
            self.log_error("get_transaction_statistics", e)
            raise ServiceError(f"Failed to get transaction statistics: {str(e)}")
    
    def get_product_transaction_history(self, product_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history for a specific product"""
        try:
            self.log_operation("get_product_transaction_history", {"product_id": product_id, "limit": limit})
            
            # Validate required fields
            self.validate_required_fields({"product_id": product_id})
            
            query = """
                SELECT 
                    st.*,
                    b.code as bin_code,
                    w.name as warehouse_name,
                    l.full_code,
                    u.username as user_name
                FROM stock_transactions st
                LEFT JOIN stock_items si ON st.stock_item_id = si.id
                LEFT JOIN bins b ON si.bin_id = b.id
                LEFT JOIN locations l ON b.location_id = l.id
                LEFT JOIN warehouses w ON l.warehouse_id = w.id
                LEFT JOIN users u ON st.user_id = u.id
                WHERE si.product_id = %s
                ORDER BY st.created_at DESC
                LIMIT %s
            """
            
            transactions = execute_query(query, [product_id, limit], fetch_all=True)
            return transactions
            
        except (ValidationError):
            raise
        except Exception as e:
            self.log_error("get_product_transaction_history", e)
            raise ServiceError(f"Failed to get product transaction history: {str(e)}")
    
    def get_warehouse_transaction_summary(self, warehouse_id: str, date_from: str = '', date_to: str = '') -> Dict[str, Any]:
        """Get transaction summary for a specific warehouse"""
        try:
            self.log_operation("get_warehouse_transaction_summary", {"warehouse_id": warehouse_id, "date_from": date_from, "date_to": date_to})
            
            # Validate required fields
            self.validate_required_fields({"warehouse_id": warehouse_id})
            
            # Build WHERE clause for date filtering
            where_conditions = ["l.warehouse_id = %s"]
            params = [warehouse_id]
            
            if date_from:
                where_conditions.append("st.created_at >= %s")
                params.append(date_from)
            
            if date_to:
                where_conditions.append("st.created_at <= %s")
                params.append(date_to)
            
            where_clause = " AND ".join(where_conditions)
            
            # Get warehouse transaction summary
            summary_query = f"""
                SELECT 
                    COUNT(*) as total_transactions,
                    COUNT(DISTINCT st.stock_item_id) as unique_stock_items,
                    COUNT(DISTINCT p.id) as unique_products,
                    SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) as total_received,
                    SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END) as total_shipped,
                    SUM(CASE WHEN st.transaction_type = 'adjust' THEN st.quantity_change ELSE 0 END) as total_adjusted
                FROM stock_transactions st
                LEFT JOIN stock_items si ON st.stock_item_id = si.id
                LEFT JOIN products p ON si.product_id = p.id
                LEFT JOIN bins b ON si.bin_id = b.id
                LEFT JOIN locations l ON b.location_id = l.id
                WHERE {where_clause}
            """
            
            summary = execute_query(summary_query, params, fetch_one=True)
            
            # Get recent transactions
            recent_query = f"""
                SELECT 
                    st.*,
                    p.sku,
                    p.name as product_name,
                    b.code as bin_code,
                    l.full_code,
                    u.username as user_name
                FROM stock_transactions st
                LEFT JOIN stock_items si ON st.stock_item_id = si.id
                LEFT JOIN products p ON si.product_id = p.id
                LEFT JOIN bins b ON si.bin_id = b.id
                LEFT JOIN locations l ON b.location_id = l.id
                LEFT JOIN users u ON st.user_id = u.id
                WHERE {where_clause}
                ORDER BY st.created_at DESC
                LIMIT 10
            """
            
            recent_transactions = execute_query(recent_query, params, fetch_all=True)
            
            return {
                "summary": summary,
                "recent_transactions": recent_transactions
            }
            
        except (ValidationError):
            raise
        except Exception as e:
            self.log_error("get_warehouse_transaction_summary", e)
            raise ServiceError(f"Failed to get warehouse transaction summary: {str(e)}")
    
    def reverse_transaction(self, transaction_id: str, user_id: str, notes: str = '') -> Dict[str, Any]:
        """Reverse a transaction by creating an opposite transaction"""
        try:
            self.log_operation("reverse_transaction", {"transaction_id": transaction_id, "user_id": user_id, "notes": notes})
            
            # Validate required fields
            self.validate_required_fields({"transaction_id": transaction_id, "user_id": user_id})
            
            # Get original transaction
            original_transaction = StockTransaction.get_by_id(transaction_id)
            if not original_transaction:
                raise NotFoundError(f"Transaction with ID {transaction_id} not found")
            
            # Check if transaction can be reversed
            if original_transaction.transaction_type in ['adjust', 'cycle_count']:
                raise ValidationError(f"Cannot reverse transaction of type '{original_transaction.transaction_type}'")
            
            # Calculate reverse quantity
            reverse_quantity = -original_transaction.quantity_change
            
            # Create reverse transaction
            reverse_transaction = self.create_transaction(
                stock_item_id=original_transaction.stock_item_id,
                transaction_type=original_transaction.transaction_type,
                quantity_change=reverse_quantity,
                user_id=user_id,
                notes=f"Reversal of transaction {transaction_id}: {notes}",
                reference_id=transaction_id
            )
            
            return reverse_transaction
            
        except (ValidationError, NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.log_error("reverse_transaction", e)
            raise ServiceError(f"Failed to reverse transaction: {str(e)}")
    
    def get_transaction_audit_trail(self, reference_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for a specific reference ID"""
        try:
            self.log_operation("get_transaction_audit_trail", {"reference_id": reference_id})
            
            # Validate required fields
            self.validate_required_fields({"reference_id": reference_id})
            
            query = """
                SELECT 
                    st.*,
                    p.sku,
                    p.name as product_name,
                    b.code as bin_code,
                    w.name as warehouse_name,
                    l.full_code,
                    u.username as user_name
                FROM stock_transactions st
                LEFT JOIN stock_items si ON st.stock_item_id = si.id
                LEFT JOIN products p ON si.product_id = p.id
                LEFT JOIN bins b ON si.bin_id = b.id
                LEFT JOIN locations l ON b.location_id = l.id
                LEFT JOIN warehouses w ON l.warehouse_id = w.id
                LEFT JOIN users u ON st.user_id = u.id
                WHERE st.reference_id = %s
                ORDER BY st.created_at ASC
            """
            
            transactions = execute_query(query, [reference_id], fetch_all=True)
            return transactions
            
        except (ValidationError):
            raise
        except Exception as e:
            self.log_error("get_transaction_audit_trail", e)
            raise ServiceError(f"Failed to get transaction audit trail: {str(e)}")
    
    def get_transactions_by_type(self, transaction_type: str) -> List[Dict[str, Any]]:
        """Get transactions by type"""
        try:
            self.log_operation("get_transactions_by_type", {"transaction_type": transaction_type})
            
            return self.transaction_repository.get_transactions_by_type(transaction_type)
            
        except Exception as e:
            self.log_error("get_transactions_by_type", e)
            return []
    
    def get_transactions_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get transactions by date range"""
        try:
            self.log_operation("get_transactions_by_date_range", {"start_date": start_date, "end_date": end_date})
            
            return self.transaction_repository.get_transactions_by_date_range(start_date, end_date)
            
        except Exception as e:
            self.log_error("get_transactions_by_date_range", e)
            return []
