"""
Stock Repository for Inventory Management System
Handles all stock-related database operations
"""

from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from backend.models.stock import StockItem


class StockRepository(BaseRepository[StockItem]):
    """Repository for stock data access"""
    
    def __init__(self):
        super().__init__(StockItem, 'stock_items')
    
    def get_stock_by_product(self, product_id: str) -> List[StockItem]:
        """Get all stock items for a specific product"""
        return self.find_by(product_id=product_id)
    
    def get_stock_by_bin(self, bin_id: str) -> Optional[StockItem]:
        """Get stock item by bin ID"""
        return self.find_one_by(bin_id=bin_id)
    
    def get_stock_by_warehouse(self, warehouse_id: str) -> List[Dict[str, Any]]:
        """Get stock items in a specific warehouse"""
        query = """
            SELECT si.*, 
                   p.name as product_name,
                   p.sku as product_sku,
                   p.barcode as product_barcode,
                   b.code as bin_code,
                   l.full_code as location_code,
                   w.name as warehouse_name
            FROM stock_items si
            INNER JOIN products p ON si.product_id = p.id
            INNER JOIN bins b ON si.bin_id = b.id
            INNER JOIN locations l ON b.location_id = l.id
            INNER JOIN warehouses w ON l.warehouse_id = w.id
            WHERE w.id = %s
            ORDER BY p.name, b.code
        """
        
        return self.execute_custom_query(query, (warehouse_id,))
    
    def get_stock_by_location(self, location_id: str) -> List[Dict[str, Any]]:
        """Get stock items in a specific location"""
        query = """
            SELECT si.*, 
                   p.name as product_name,
                   p.sku as product_sku,
                   p.barcode as product_barcode,
                   b.code as bin_code,
                   l.full_code as location_code,
                   w.name as warehouse_name
            FROM stock_items si
            INNER JOIN products p ON si.product_id = p.id
            INNER JOIN bins b ON si.bin_id = b.id
            INNER JOIN locations l ON b.location_id = l.id
            INNER JOIN warehouses w ON l.warehouse_id = w.id
            WHERE l.id = %s
            ORDER BY p.name, b.code
        """
        
        return self.execute_custom_query(query, (location_id,))
    
    def get_stock_levels(self) -> List[Dict[str, Any]]:
        """Get current stock levels for all products"""
        query = """
            SELECT p.id as product_id,
                   p.name as product_name,
                   p.sku as product_sku,
                   p.barcode as product_barcode,
                   COALESCE(SUM(si.on_hand), 0) as total_stock,
                   COALESCE(SUM(si.qty_reserved), 0) as total_reserved,
                   COALESCE(SUM(si.on_hand - si.qty_reserved), 0) as available_stock,
                   COUNT(si.id) as stock_locations
            FROM products p
            LEFT JOIN stock_items si ON p.id = si.product_id
            GROUP BY p.id, p.name, p.sku, p.barcode
            ORDER BY available_stock ASC, p.name
        """
        
        return self.execute_custom_query(query)
    
    def get_low_stock_items(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """Get stock items below threshold"""
        query = """
            SELECT si.*, 
                   p.name as product_name,
                   p.sku as product_sku,
                   p.barcode as product_barcode,
                   b.code as bin_code,
                   l.full_code as location_code,
                   w.name as warehouse_name,
                   (si.on_hand - si.qty_reserved) as available_stock
            FROM stock_items si
            INNER JOIN products p ON si.product_id = p.id
            INNER JOIN bins b ON si.bin_id = b.id
            INNER JOIN locations l ON b.location_id = l.id
            INNER JOIN warehouses w ON l.warehouse_id = w.id
            WHERE (si.on_hand - si.qty_reserved) <= %s
            ORDER BY available_stock ASC, p.name
        """
        
        return self.execute_custom_query(query, (threshold,))
    
    def get_out_of_stock_items(self) -> List[Dict[str, Any]]:
        """Get stock items with no available stock"""
        query = """
            SELECT si.*, 
                   p.name as product_name,
                   p.sku as product_sku,
                   p.barcode as product_barcode,
                   b.code as bin_code,
                   l.full_code as location_code,
                   w.name as warehouse_name,
                   (si.on_hand - si.qty_reserved) as available_stock
            FROM stock_items si
            INNER JOIN products p ON si.product_id = p.id
            INNER JOIN bins b ON si.bin_id = b.id
            INNER JOIN locations l ON b.location_id = l.id
            INNER JOIN warehouses w ON l.warehouse_id = w.id
            WHERE (si.on_hand - si.qty_reserved) <= 0
            ORDER BY p.name, b.code
        """
        
        return self.execute_custom_query(query)
    
    def get_expiring_stock(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get stock items expiring soon"""
        query = """
            SELECT si.*, 
                   p.name as product_name,
                   p.sku as product_sku,
                   p.barcode as product_barcode,
                   b.code as bin_code,
                   l.full_code as location_code,
                   w.name as warehouse_name,
                   EXTRACT(DAYS FROM (si.expiry_date - CURRENT_DATE)) as days_until_expiry
            FROM stock_items si
            INNER JOIN products p ON si.product_id = p.id
            INNER JOIN bins b ON si.bin_id = b.id
            INNER JOIN locations l ON b.location_id = l.id
            INNER JOIN warehouses w ON l.warehouse_id = w.id
            WHERE si.expiry_date IS NOT NULL 
              AND si.expiry_date <= CURRENT_DATE + INTERVAL '%s days'
              AND si.on_hand > 0
            ORDER BY si.expiry_date ASC, p.name
        """
        
        return self.execute_custom_query(query, (days_ahead,))
    
    def get_stock_movements(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get stock movement history"""
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
            WHERE st.created_at >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY st.created_at DESC
        """
        
        return self.execute_custom_query(query, (days,))
    
    def get_stock_statistics(self) -> Dict[str, Any]:
        """Get stock statistics for dashboard"""
        query = """
            SELECT 
                COUNT(*) as total_stock_items,
                COUNT(CASE WHEN on_hand > 0 THEN 1 END) as in_stock_items,
                COUNT(CASE WHEN on_hand = 0 THEN 1 END) as out_of_stock_items,
                COUNT(CASE WHEN (on_hand - qty_reserved) <= 10 AND (on_hand - qty_reserved) > 0 THEN 1 END) as low_stock_items,
                SUM(on_hand) as total_quantity,
                SUM(qty_reserved) as total_reserved,
                SUM(on_hand - qty_reserved) as total_available
            FROM stock_items
        """
        
        return self.execute_custom_query_single(query) or {}
    
    def get_stock_by_batch(self, batch_id: str) -> List[StockItem]:
        """Get stock items by batch ID"""
        return self.find_by(batch_id=batch_id)
    
    def get_stock_by_expiry_date(self, expiry_date: str) -> List[StockItem]:
        """Get stock items by expiry date"""
        return self.find_by(expiry_date=expiry_date)
    
    def get_stock_transactions(self, stock_item_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get transaction history for a specific stock item"""
        query = """
            SELECT st.*,
                   u.username as user_name
            FROM stock_transactions st
            LEFT JOIN users u ON st.user_id = u.id
            WHERE st.stock_item_id = %s
            ORDER BY st.created_at DESC
        """
        
        params = [stock_item_id]
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        return self.execute_custom_query(query, tuple(params))
    
    def reserve_stock(self, stock_item_id: str, quantity: int, user_id: str) -> bool:
        """Reserve stock for an order"""
        try:
            with self.get_cursor() as cursor:
                # Check if enough stock is available
                cursor.execute(
                    """
                    SELECT on_hand, qty_reserved 
                    FROM stock_items 
                    WHERE id = %s
                    """,
                    (stock_item_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    return False
                
                on_hand, qty_reserved = result
                available = on_hand - qty_reserved
                
                if available < quantity:
                    return False
                
                # Update reserved quantity
                cursor.execute(
                    """
                    UPDATE stock_items 
                    SET qty_reserved = qty_reserved + %s 
                    WHERE id = %s
                    """,
                    (quantity, stock_item_id)
                )
                
                # Log the transaction
                cursor.execute(
                    """
                    INSERT INTO stock_transactions 
                    (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, notes)
                    VALUES (%s, 'reserve', %s, %s, %s, %s, 'Stock reserved')
                    """,
                    (stock_item_id, -quantity, qty_reserved, qty_reserved + quantity, user_id)
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to reserve stock: {e}")
            return False
    
    def release_stock(self, stock_item_id: str, quantity: int, user_id: str) -> bool:
        """Release reserved stock"""
        try:
            with self.get_cursor() as cursor:
                # Update reserved quantity
                cursor.execute(
                    """
                    UPDATE stock_items 
                    SET qty_reserved = GREATEST(0, qty_reserved - %s) 
                    WHERE id = %s
                    """,
                    (quantity, stock_item_id)
                )
                
                # Log the transaction
                cursor.execute(
                    """
                    INSERT INTO stock_transactions 
                    (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, notes)
                    VALUES (%s, 'release', %s, 
                           (SELECT qty_reserved FROM stock_items WHERE id = %s) + %s,
                           (SELECT qty_reserved FROM stock_items WHERE id = %s),
                           %s, 'Stock reservation released')
                    """,
                    (stock_item_id, quantity, stock_item_id, quantity, stock_item_id, user_id)
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to release stock: {e}")
            return False
