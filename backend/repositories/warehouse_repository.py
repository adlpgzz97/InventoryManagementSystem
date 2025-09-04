"""
Warehouse Repository for Inventory Management System
Handles all warehouse-related database operations
"""

from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from backend.models.warehouse import Warehouse


class WarehouseRepository(BaseRepository[Warehouse]):
    """Repository for warehouse data access"""
    
    def __init__(self):
        super().__init__(Warehouse, 'warehouses')
    
    def get_by_code(self, code: str) -> Optional[Warehouse]:
        """Get warehouse by code"""
        return self.find_one_by(code=code)
    
    def get_warehouse_hierarchy(self) -> List[Dict[str, Any]]:
        """Get complete warehouse hierarchy with locations and bins"""
        query = """
            SELECT w.id as warehouse_id,
                   w.name as warehouse_name,
                   w.code as warehouse_code,
                   w.address as warehouse_address,
                   l.id as location_id,
                   l.full_code as location_code,
                   b.id as bin_id,
                   b.code as bin_code,
                   COUNT(si.id) as stock_items_count,
                   COALESCE(SUM(si.on_hand), 0) as total_stock
            FROM warehouses w
            LEFT JOIN locations l ON w.id = l.warehouse_id
            LEFT JOIN bins b ON l.id = b.location_id
            LEFT JOIN stock_items si ON b.id = si.bin_id
            GROUP BY w.id, w.name, w.code, w.address, l.id, l.full_code, b.id, b.code
            ORDER BY w.name, l.full_code, b.code
        """
        
        return self.execute_custom_query(query)
    
    def get_warehouse_stock_summary(self, warehouse_id: str) -> Dict[str, Any]:
        """Get stock summary for a specific warehouse"""
        query = """
            SELECT w.name as warehouse_name,
                   w.code as warehouse_code,
                   COUNT(DISTINCT l.id) as total_locations,
                   COUNT(DISTINCT b.id) as total_bins,
                   COUNT(DISTINCT si.id) as total_stock_items,
                   COUNT(DISTINCT si.product_id) as unique_products,
                   COALESCE(SUM(si.on_hand), 0) as total_quantity,
                   COALESCE(SUM(si.qty_reserved), 0) as total_reserved,
                   COALESCE(SUM(si.on_hand - si.qty_reserved), 0) as total_available
            FROM warehouses w
            LEFT JOIN locations l ON w.id = l.warehouse_id
            LEFT JOIN bins b ON l.id = b.location_id
            LEFT JOIN stock_items si ON b.id = si.bin_id
            WHERE w.id = %s
            GROUP BY w.id, w.name, w.code
        """
        
        return self.execute_custom_query_single(query, (warehouse_id,)) or {}
    
    def get_warehouse_capacity_utilization(self, warehouse_id: str) -> Dict[str, Any]:
        """Get capacity utilization for a warehouse"""
        query = """
            SELECT w.name as warehouse_name,
                   COUNT(DISTINCT b.id) as total_bins,
                   COUNT(CASE WHEN si.id IS NOT NULL THEN b.id END) as occupied_bins,
                   ROUND(
                       (COUNT(CASE WHEN si.id IS NOT NULL THEN b.id END)::float / 
                        COUNT(DISTINCT b.id)::float) * 100, 2
                   ) as utilization_percentage
            FROM warehouses w
            LEFT JOIN locations l ON w.id = l.warehouse_id
            LEFT JOIN bins b ON l.id = b.location_id
            LEFT JOIN stock_items si ON b.id = si.bin_id
            WHERE w.id = %s
            GROUP BY w.id, w.name
        """
        
        return self.execute_custom_query_single(query, (warehouse_id,)) or {}
    
    def get_empty_locations(self, warehouse_id: str) -> List[Dict[str, Any]]:
        """Get empty locations in a warehouse"""
        query = """
            SELECT l.id as location_id,
                   l.full_code as location_code,
                   b.id as bin_id,
                   b.code as bin_code
            FROM warehouses w
            INNER JOIN locations l ON w.id = l.warehouse_id
            INNER JOIN bins b ON l.id = b.location_id
            LEFT JOIN stock_items si ON b.id = si.bin_id
            WHERE w.id = %s AND si.id IS NULL
            ORDER BY l.full_code, b.code
        """
        
        return self.execute_custom_query(query, (warehouse_id,))
    
    def get_warehouse_statistics(self) -> Dict[str, Any]:
        """Get overall warehouse statistics"""
        query = """
            SELECT 
                COUNT(*) as total_warehouses,
                COUNT(CASE WHEN code IS NOT NULL THEN 1 END) as coded_warehouses,
                COUNT(CASE WHEN address IS NOT NULL THEN 1 END) as addressed_warehouses
            FROM warehouses
        """
        
        return self.execute_custom_query_single(query) or {}
    
    def get_warehouse_by_location(self, location_id: str) -> Optional[Warehouse]:
        """Get warehouse by location ID"""
        query = """
            SELECT w.*
            FROM warehouses w
            INNER JOIN locations l ON w.id = l.warehouse_id
            WHERE l.id = %s
        """
        
        result = self.execute_custom_query_single(query, (location_id,))
        if result:
            return Warehouse.from_dict(result)
        return None
    
    def get_warehouse_by_bin(self, bin_id: str) -> Optional[Warehouse]:
        """Get warehouse by bin ID"""
        query = """
            SELECT w.*
            FROM warehouses w
            INNER JOIN locations l ON w.id = l.warehouse_id
            INNER JOIN bins b ON l.id = b.location_id
            WHERE b.id = %s
        """
        
        result = self.execute_custom_query_single(query, (bin_id,))
        if result:
            return Warehouse.from_dict(result)
        return None
    
    def search_warehouses(self, search_term: str) -> List[Warehouse]:
        """Search warehouses by name, code, or address"""
        if not search_term:
            return self.get_all()
        
        query = """
            SELECT * FROM warehouses 
            WHERE name ILIKE %s 
               OR code ILIKE %s 
               OR address ILIKE %s
            ORDER BY name
        """
        
        search_pattern = f"%{search_term}%"
        params = (search_pattern, search_pattern, search_pattern)
        
        results = self.execute_custom_query(query, params)
        return [Warehouse.from_dict(result) for result in results]
    
    def get_warehouse_locations(self, warehouse_id: str) -> List[Dict[str, Any]]:
        """Get all locations in a warehouse"""
        query = """
            SELECT l.id as location_id,
                   l.full_code as location_code,
                   COUNT(b.id) as bin_count,
                   COUNT(CASE WHEN si.id IS NOT NULL THEN b.id END) as occupied_bins
            FROM warehouses w
            INNER JOIN locations l ON w.id = l.warehouse_id
            LEFT JOIN bins b ON l.id = b.location_id
            LEFT JOIN stock_items si ON b.id = si.bin_id
            WHERE w.id = %s
            GROUP BY l.id, l.full_code
            ORDER BY l.full_code
        """
        
        return self.execute_custom_query(query, (warehouse_id,))
    
    def get_warehouse_bins(self, warehouse_id: str) -> List[Dict[str, Any]]:
        """Get all bins in a warehouse"""
        query = """
            SELECT b.id as bin_id,
                   b.code as bin_code,
                   l.id as location_id,
                   l.full_code as location_code,
                   CASE WHEN si.id IS NOT NULL THEN true ELSE false END as is_occupied,
                   si.product_id,
                   p.name as product_name,
                   si.on_hand as stock_quantity
            FROM warehouses w
            INNER JOIN locations l ON w.id = l.warehouse_id
            INNER JOIN bins b ON l.id = b.location_id
            LEFT JOIN stock_items si ON b.id = si.bin_id
            LEFT JOIN products p ON si.product_id = p.id
            WHERE w.id = %s
            ORDER BY l.full_code, b.code
        """
        
        return self.execute_custom_query(query, (warehouse_id,))
    
    def add_location_to_warehouse(self, warehouse_id: str, location_code: str) -> bool:
        """Add a new location to a warehouse"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO locations (warehouse_id, full_code)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (warehouse_id, location_code)
                )
                return True
        except Exception as e:
            self.logger.error(f"Failed to add location to warehouse: {e}")
            return False
    
    def add_bin_to_location(self, location_id: str, bin_code: str) -> bool:
        """Add a new bin to a location"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO bins (code, location_id)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (bin_code, location_id)
                )
                return True
        except Exception as e:
            self.logger.error(f"Failed to add bin to location: {e}")
            return False
