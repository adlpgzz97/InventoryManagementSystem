"""
Transaction Repository for Inventory Management System
Handles all transaction-related database operations
"""

from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from backend.models.stock import StockTransaction


class TransactionRepository(BaseRepository[StockTransaction]):
    """Repository for transaction data access"""
    
    def __init__(self):
        super().__init__(StockTransaction, 'stock_transactions')
    
    def get_transactions_by_type(self, transaction_type: str) -> List[StockTransaction]:
        """Get transactions by type"""
        return self.find_by(transaction_type=transaction_type)
    
    def get_transactions_by_user(self, user_id: str) -> List[StockTransaction]:
        """Get transactions by user"""
        return self.find_by(user_id=user_id)
    
    def get_transactions_by_stock_item(self, stock_item_id: str) -> List[StockTransaction]:
        """Get transactions for a specific stock item"""
        return self.find_by(stock_item_id=stock_item_id)
    
    def get_transactions_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get transactions within a date range"""
        query = """
            SELECT st.*,
                   p.name as product_name,
                   p.sku as product_sku,
                   u.username as user_name,
                   si.bin_id,
                   b.code as bin_code,
                   l.full_code as location_code,
                   w.name as warehouse_name
            FROM stock_transactions st
            INNER JOIN stock_items si ON st.stock_item_id = si.id
            INNER JOIN products p ON si.product_id = p.id
            LEFT JOIN users u ON st.user_id = u.id
            INNER JOIN bins b ON si.bin_id = b.id
            INNER JOIN locations l ON b.location_id = l.id
            INNER JOIN warehouses w ON l.warehouse_id = w.id
            WHERE st.created_at >= %s AND st.created_at <= %s
            ORDER BY st.created_at DESC
        """
        
        return self.execute_custom_query(query, (start_date, end_date))
    
    def get_transactions_by_warehouse(self, warehouse_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get transactions for a specific warehouse"""
        query = """
            SELECT st.*,
                   p.name as product_name,
                   p.sku as product_sku,
                   u.username as user_name,
                   si.bin_id,
                   b.code as bin_code,
                   l.full_code as location_code,
                   w.name as warehouse_name
            FROM stock_transactions st
            INNER JOIN stock_items si ON st.stock_item_id = si.id
            INNER JOIN products p ON si.product_id = p.id
            LEFT JOIN users u ON st.user_id = u.id
            INNER JOIN bins b ON si.bin_id = b.id
            INNER JOIN locations l ON b.location_id = l.id
            INNER JOIN warehouses w ON l.warehouse_id = w.id
            WHERE w.id = %s 
              AND st.created_at >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY st.created_at DESC
        """
        
        return self.execute_custom_query(query, (warehouse_id, days))
    
    def get_transaction_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get transaction statistics for dashboard"""
        query = """
            SELECT 
                COUNT(*) as total_transactions,
                COUNT(CASE WHEN transaction_type = 'receive' THEN 1 END) as receive_count,
                COUNT(CASE WHEN transaction_type = 'ship' THEN 1 END) as ship_count,
                COUNT(CASE WHEN transaction_type = 'adjust' THEN 1 END) as adjust_count,
                COUNT(CASE WHEN transaction_type = 'transfer' THEN 1 END) as transfer_count,
                COUNT(CASE WHEN transaction_type = 'reserve' THEN 1 END) as reserve_count,
                COUNT(CASE WHEN transaction_type = 'release' THEN 1 END) as release_count,
                SUM(CASE WHEN transaction_type = 'receive' THEN quantity_change ELSE 0 END) as total_received,
                SUM(CASE WHEN transaction_type = 'ship' THEN ABS(quantity_change) ELSE 0 END) as total_shipped,
                COUNT(DISTINCT user_id) as active_users,
                COUNT(DISTINCT stock_item_id) as affected_stock_items
            FROM stock_transactions
            WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
        """
        
        return self.execute_custom_query_single(query, (days,)) or {}
    
    def get_transaction_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get transaction trends over time"""
        query = """
            SELECT 
                DATE(st.created_at) as transaction_date,
                COUNT(*) as transaction_count,
                COUNT(CASE WHEN st.transaction_type = 'receive' THEN 1 END) as receive_count,
                COUNT(CASE WHEN st.transaction_type = 'ship' THEN 1 END) as ship_count,
                COUNT(CASE WHEN st.transaction_type = 'adjust' THEN 1 END) as adjust_count,
                SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) as total_received,
                SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END) as total_shipped
            FROM stock_transactions st
            WHERE st.created_at >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(st.created_at)
            ORDER BY transaction_date DESC
        """
        
        return self.execute_custom_query(query, (days,))
    
    def get_user_transaction_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get transaction summary for a specific user"""
        query = """
            SELECT 
                u.username,
                COUNT(st.id) as total_transactions,
                COUNT(CASE WHEN st.transaction_type = 'receive' THEN 1 END) as receive_count,
                COUNT(CASE WHEN st.transaction_type = 'ship' THEN 1 END) as ship_count,
                COUNT(CASE WHEN st.transaction_type = 'adjust' THEN 1 END) as adjust_count,
                COUNT(CASE WHEN st.transaction_type = 'transfer' THEN 1 END) as transfer_count,
                COUNT(CASE WHEN st.transaction_type = 'reserve' THEN 1 END) as reserve_count,
                COUNT(CASE WHEN st.transaction_type = 'release' THEN 1 END) as release_count,
                SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) as total_received,
                SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END) as total_shipped,
                MAX(st.created_at) as last_activity
            FROM users u
            LEFT JOIN stock_transactions st ON u.id = st.user_id
            WHERE u.id = %s 
              AND (st.created_at >= CURRENT_DATE - INTERVAL '%s days' OR st.created_at IS NULL)
            GROUP BY u.id, u.username
        """
        
        return self.execute_custom_query_single(query, (user_id, days)) or {}
    
    def get_product_transaction_summary(self, product_id: str, days: int = 30) -> Dict[str, Any]:
        """Get transaction summary for a specific product"""
        query = """
            SELECT 
                p.name as product_name,
                p.sku as product_sku,
                COUNT(st.id) as total_transactions,
                COUNT(CASE WHEN st.transaction_type = 'receive' THEN 1 END) as receive_count,
                COUNT(CASE WHEN st.transaction_type = 'ship' THEN 1 END) as ship_count,
                COUNT(CASE WHEN st.transaction_type = 'adjust' THEN 1 END) as adjust_count,
                COUNT(CASE WHEN st.transaction_type = 'transfer' THEN 1 END) as transfer_count,
                SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) as total_received,
                SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END) as total_shipped,
                MAX(st.created_at) as last_activity
            FROM products p
            LEFT JOIN stock_items si ON p.id = si.product_id
            LEFT JOIN stock_transactions st ON si.id = st.stock_item_id
            WHERE p.id = %s 
              AND (st.created_at >= CURRENT_DATE - INTERVAL '%s days' OR st.created_at IS NULL)
            GROUP BY p.id, p.name, p.sku
        """
        
        return self.execute_custom_query_single(query, (product_id, days)) or {}
    
    def get_warehouse_transaction_summary(self, warehouse_id: str, days: int = 30) -> Dict[str, Any]:
        """Get transaction summary for a specific warehouse"""
        query = """
            SELECT 
                w.name as warehouse_name,
                w.code as warehouse_code,
                COUNT(st.id) as total_transactions,
                COUNT(CASE WHEN st.transaction_type = 'receive' THEN 1 END) as receive_count,
                COUNT(CASE WHEN st.transaction_type = 'ship' THEN 1 END) as ship_count,
                COUNT(CASE WHEN st.transaction_type = 'adjust' THEN 1 END) as adjust_count,
                COUNT(CASE WHEN st.transaction_type = 'transfer' THEN 1 END) as transfer_count,
                COUNT(CASE WHEN st.transaction_type = 'reserve' THEN 1 END) as reserve_count,
                COUNT(CASE WHEN st.transaction_type = 'release' THEN 1 END) as release_count,
                SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) as total_received,
                SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END) as total_shipped,
                COUNT(DISTINCT st.user_id) as active_users,
                MAX(st.created_at) as last_activity
            FROM warehouses w
            LEFT JOIN locations l ON w.id = l.warehouse_id
            LEFT JOIN bins b ON l.id = b.location_id
            LEFT JOIN stock_items si ON b.id = si.bin_id
            LEFT JOIN stock_transactions st ON si.id = st.stock_item_id
            WHERE w.id = %s 
              AND (st.created_at >= CURRENT_DATE - INTERVAL '%s days' OR st.created_at IS NULL)
            GROUP BY w.id, w.name, w.code
        """
        
        return self.execute_custom_query_single(query, (warehouse_id, days)) or {}
    
    def get_transaction_audit_trail(self, reference_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for a specific reference (order, shipment, etc.)"""
        query = """
            SELECT st.*,
                   p.name as product_name,
                   p.sku as product_sku,
                   u.username as user_name,
                   si.bin_id,
                   b.code as bin_code,
                   l.full_code as location_code,
                   w.name as warehouse_name
            FROM stock_transactions st
            INNER JOIN stock_items si ON st.stock_item_id = si.id
            INNER JOIN products p ON si.product_id = p.id
            LEFT JOIN users u ON st.user_id = u.id
            INNER JOIN bins b ON si.bin_id = b.id
            INNER JOIN locations l ON b.location_id = l.id
            INNER JOIN warehouses w ON l.warehouse_id = w.id
            WHERE st.reference_id = %s
            ORDER BY st.created_at ASC
        """
        
        return self.execute_custom_query(query, (reference_id,))
    
    def get_transaction_types_summary(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get summary of transaction types"""
        query = """
            SELECT 
                transaction_type,
                COUNT(*) as count,
                SUM(quantity_change) as total_quantity_change,
                AVG(quantity_change) as avg_quantity_change,
                MIN(quantity_change) as min_quantity_change,
                MAX(quantity_change) as max_quantity_change
            FROM stock_transactions
            WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY transaction_type
            ORDER BY count DESC
        """
        
        return self.execute_custom_query(query, (days,))
    
    def get_transaction_volume_by_hour(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get transaction volume by hour of day"""
        query = """
            SELECT 
                EXTRACT(HOUR FROM created_at) as hour_of_day,
                COUNT(*) as transaction_count,
                COUNT(DISTINCT user_id) as active_users
            FROM stock_transactions
            WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY EXTRACT(HOUR FROM created_at)
            ORDER BY hour_of_day
        """
        
        return self.execute_custom_query(query, (days,))
    
    def get_transaction_volume_by_day_of_week(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get transaction volume by day of week"""
        query = """
            SELECT 
                EXTRACT(DOW FROM created_at) as day_of_week,
                TO_CHAR(created_at, 'Day') as day_name,
                COUNT(*) as transaction_count,
                COUNT(DISTINCT user_id) as active_users
            FROM stock_transactions
            WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY EXTRACT(DOW FROM created_at), TO_CHAR(created_at, 'Day')
            ORDER BY day_of_week
        """
        
        return self.execute_custom_query(query, (days,))
