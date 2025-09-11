"""
Product Repository for Inventory Management System
Handles all product-related database operations
"""

from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from backend.models.product import Product


class ProductRepository(BaseRepository[Product]):
    """Repository for product data access"""
    
    def __init__(self):
        super().__init__(Product, 'products')
    
    def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU"""
        return self.find_one_by(sku=sku)
    
    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        """Get product by barcode"""
        return self.find_one_by(barcode=barcode)
    
    def search_products(self, search_term: str, limit: Optional[int] = None) -> List[Product]:
        """Search products by name, description, or SKU"""
        if not search_term:
            return self.get_all(limit=limit)
        
        query = """
            SELECT * FROM products 
            WHERE name ILIKE %s 
               OR description ILIKE %s 
               OR sku ILIKE %s
            ORDER BY name
        """
        
        search_pattern = f"%{search_term}%"
        params = (search_pattern, search_pattern, search_pattern)
        
        results = self.execute_custom_query(query, params)
        return [Product.from_dict(result) for result in results]
    
    def get_products_by_category(self, category: str) -> List[Product]:
        """Get products by category"""
        # Note: This assumes products have a category field
        # If not, this method can be removed or modified
        return self.find_by(category=category)
    
    def get_batch_tracked_products(self) -> List[Product]:
        """Get all products that require batch tracking"""
        return self.find_by(batch_tracked=True)
    
    def get_products_with_stock(self) -> List[Dict[str, Any]]:
        """Get products with their current stock levels"""
        query = """
            SELECT p.*, 
                   COALESCE(SUM(si.on_hand), 0) as total_stock,
                   COALESCE(SUM(si.qty_reserved), 0) as total_reserved,
                   COALESCE(SUM(si.on_hand - si.qty_reserved), 0) as available_stock
            FROM products p
            LEFT JOIN stock_items si ON p.id = si.product_id
            GROUP BY p.id, p.name, p.sku, p.description, p.dimensions, 
                     p.weight, p.picture_url, p.barcode, p.created_at, p.batch_tracked
            ORDER BY p.name
        """
        
        return self.execute_custom_query(query)
    
    def get_low_stock_products(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """Get products with stock below threshold"""
        query = """
            SELECT p.*, 
                   COALESCE(SUM(si.on_hand), 0) as total_stock,
                   COALESCE(SUM(si.qty_reserved), 0) as total_reserved,
                   COALESCE(SUM(si.on_hand - si.qty_reserved), 0) as available_stock
            FROM products p
            LEFT JOIN stock_items si ON p.id = si.product_id
            GROUP BY p.id, p.name, p.sku, p.description, p.dimensions, 
                     p.weight, p.picture_url, p.barcode, p.created_at, p.batch_tracked
            HAVING COALESCE(SUM(si.on_hand - si.qty_reserved), 0) <= %s
            ORDER BY available_stock ASC
        """
        
        return self.execute_custom_query(query, (threshold,))
    
    def get_out_of_stock_products(self) -> List[Dict[str, Any]]:
        """Get products with no available stock"""
        query = """
            SELECT p.*, 
                   COALESCE(SUM(si.on_hand), 0) as total_stock,
                   COALESCE(SUM(si.qty_reserved), 0) as total_reserved,
                   COALESCE(SUM(si.on_hand - si.qty_reserved), 0) as available_stock
            FROM products p
            LEFT JOIN stock_items si ON p.id = si.product_id
            GROUP BY p.id, p.name, p.sku, p.description, p.dimensions, 
                     p.weight, p.picture_url, p.barcode, p.created_at, p.batch_tracked
            HAVING COALESCE(SUM(si.on_hand - si.qty_reserved), 0) <= 0
            ORDER BY p.name
        """
        
        return self.execute_custom_query(query)
    
    def get_products_by_warehouse(self, warehouse_id: str) -> List[Dict[str, Any]]:
        """Get products available in a specific warehouse"""
        query = """
            SELECT p.*, 
                   si.on_hand,
                   si.qty_reserved,
                   (si.on_hand - si.qty_reserved) as available_stock,
                   si.bin_id,
                   b.code as bin_code,
                   l.full_code as location_code,
                   w.name as warehouse_name
            FROM products p
            INNER JOIN stock_items si ON p.id = si.product_id
            INNER JOIN bins b ON si.bin_id = b.id
            INNER JOIN locations l ON b.location_id = l.id
            INNER JOIN warehouses w ON l.warehouse_id = w.id
            WHERE w.id = %s AND si.on_hand > 0
            ORDER BY p.name
        """
        
        return self.execute_custom_query(query, (warehouse_id,))
    
    def get_product_statistics(self) -> Dict[str, Any]:
        """Get product statistics for dashboard"""
        query = """
            SELECT 
                COUNT(*) as total_products,
                COUNT(CASE WHEN batch_tracked = true THEN 1 END) as batch_tracked_products,
                COUNT(CASE WHEN batch_tracked = false THEN 1 END) as non_batch_products
            FROM products
        """
        
        result = self.execute_custom_query_single(query)
        return result or {}
    
    def get_products_with_expiring_batches(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get products with batches expiring soon"""
        query = """
            SELECT p.*, 
                   si.batch_id,
                   si.expiry_date,
                   si.on_hand,
                   (si.expiry_date::date - CURRENT_DATE) as days_until_expiry
            FROM products p
            INNER JOIN stock_items si ON p.id = si.product_id
            WHERE si.expiry_date IS NOT NULL 
              AND si.expiry_date <= CURRENT_DATE + make_interval(days => %s)
              AND si.on_hand > 0
            ORDER BY si.expiry_date ASC
        """
        
        return self.execute_custom_query(query, (days_ahead,))
    
    def get_product_usage_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get product usage statistics based on transactions"""
        query = """
            SELECT p.id, p.name, p.sku,
                   COUNT(st.id) as transaction_count,
                   SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END) as shipped_qty,
                   SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) as received_qty
            FROM products p
            LEFT JOIN stock_items si ON p.id = si.product_id
            LEFT JOIN stock_transactions st ON si.id = st.stock_item_id
            WHERE st.created_at >= CURRENT_DATE - INTERVAL '%s days'
               OR st.created_at IS NULL
            GROUP BY p.id, p.name, p.sku
            ORDER BY transaction_count DESC, shipped_qty DESC
        """
        
        return self.execute_custom_query(query, (days,))
