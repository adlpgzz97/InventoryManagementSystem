"""
Product model for Inventory Management System
Handles product data, validation, and database operations
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from utils.database import execute_query

# Configure logging
logger = logging.getLogger(__name__)


class Product:
    """Product model for inventory management"""
    
    def __init__(self, id: str, name: str, description: str = None, sku: str = None,
                 barcode: str = None, category: str = None, unit: str = None,
                 batch_tracked: bool = False, min_stock_level: int = 0,
                 max_stock_level: int = None, created_at: datetime = None,
                 updated_at: datetime = None):
        self.id = id
        self.name = name
        self.description = description
        self.sku = sku
        self.barcode = barcode
        self.category = category
        self.unit = unit
        self.batch_tracked = batch_tracked
        self.min_stock_level = min_stock_level
        self.max_stock_level = max_stock_level
        self.created_at = created_at
        self.updated_at = updated_at
    
    def __repr__(self):
        return f"<Product {self.name} (ID: {self.id})>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """Create Product instance from dictionary"""
        return cls(
            id=str(data['id']),
            name=data['name'],
            description=data.get('description'),
            sku=data.get('sku'),
            barcode=data.get('barcode'),
            category=data.get('category'),
            unit=data.get('unit'),
            batch_tracked=data.get('batch_tracked', False),
            min_stock_level=data.get('min_stock_level', 0),
            max_stock_level=data.get('max_stock_level'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'sku': self.sku,
            'barcode': self.barcode,
            'category': self.category,
            'unit': self.unit,
            'batch_tracked': self.batch_tracked,
            'min_stock_level': self.min_stock_level,
            'max_stock_level': self.max_stock_level,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def get_by_id(cls, product_id: str) -> Optional['Product']:
        """Get product by ID"""
        try:
            result = execute_query(
                """
                SELECT id, name, description, sku, barcode, category, unit,
                       batch_tracked, min_stock_level, max_stock_level,
                       created_at, updated_at
                FROM products WHERE id = %s
                """,
                (product_id,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting product by ID {product_id}: {e}")
            return None
    
    @classmethod
    def get_by_barcode(cls, barcode: str) -> Optional['Product']:
        """Get product by barcode"""
        try:
            result = execute_query(
                """
                SELECT id, name, description, sku, barcode, category, unit,
                       batch_tracked, min_stock_level, max_stock_level,
                       created_at, updated_at
                FROM products WHERE barcode = %s
                """,
                (barcode,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting product by barcode {barcode}: {e}")
            return None
    
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> List['Product']:
        """Get all products with optional pagination"""
        try:
            query = """
                SELECT id, name, description, sku, barcode, category, unit,
                       batch_tracked, min_stock_level, max_stock_level,
                       created_at, updated_at
                FROM products
                ORDER BY name
            """
            
            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
            
            results = execute_query(query, fetch_all=True)
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting all products: {e}")
            return []
    
    @classmethod
    def search(cls, search_term: str) -> List['Product']:
        """Search products by name, description, or SKU"""
        try:
            search_pattern = f"%{search_term}%"
            
            results = execute_query(
                """
                SELECT id, name, description, sku, barcode, category, unit,
                       batch_tracked, min_stock_level, max_stock_level,
                       created_at, updated_at
                FROM products
                WHERE name ILIKE %s OR description ILIKE %s OR sku ILIKE %s
                ORDER BY name
                """,
                (search_pattern, search_pattern, search_pattern),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []
    
    @classmethod
    def create(cls, name: str, description: str = None, sku: str = None,
               barcode: str = None, category: str = None, unit: str = None,
               batch_tracked: bool = False, min_stock_level: int = 0,
               max_stock_level: int = None) -> Optional['Product']:
        """Create a new product"""
        try:
            result = execute_query(
                """
                INSERT INTO products (name, description, sku, barcode, category, unit,
                                    batch_tracked, min_stock_level, max_stock_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, sku, barcode, category, unit,
                          batch_tracked, min_stock_level, max_stock_level,
                          created_at, updated_at
                """,
                (name, description, sku, barcode, category, unit,
                 batch_tracked, min_stock_level, max_stock_level),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating product {name}: {e}")
            return None
    
    def update(self, **kwargs) -> bool:
        """Update product attributes"""
        try:
            # Build dynamic update query
            fields = []
            values = []
            
            for key, value in kwargs.items():
                if hasattr(self, key):
                    fields.append(f"{key} = %s")
                    values.append(value)
            
            if not fields:
                return False
            
            values.append(self.id)
            
            query = f"""
                UPDATE products 
                SET {', '.join(fields)}, updated_at = NOW()
                WHERE id = %s
                RETURNING id
            """
            
            result = execute_query(query, tuple(values), fetch_one=True)
            
            if result:
                # Update instance attributes
                for key, value in kwargs.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating product {self.id}: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete product"""
        try:
            result = execute_query(
                "DELETE FROM products WHERE id = %s RETURNING id",
                (self.id,),
                fetch_one=True
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error deleting product {self.id}: {e}")
            return False
    
    def get_stock_levels(self) -> Dict[str, Any]:
        """Get current stock levels for this product"""
        try:
            result = execute_query(
                """
                SELECT 
                    COALESCE(SUM(on_hand), 0) as total_on_hand,
                    COALESCE(SUM(qty_reserved), 0) as total_reserved,
                    COALESCE(SUM(on_hand - qty_reserved), 0) as available_stock
                FROM stock_items 
                WHERE product_id = %s
                """,
                (self.id,),
                fetch_one=True
            )
            
            return result or {
                'total_on_hand': 0,
                'total_reserved': 0,
                'available_stock': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting stock levels for product {self.id}: {e}")
            return {
                'total_on_hand': 0,
                'total_reserved': 0,
                'available_stock': 0
            }
    
    def is_low_stock(self) -> bool:
        """Check if product is below minimum stock level"""
        stock_levels = self.get_stock_levels()
        return stock_levels['available_stock'] <= self.min_stock_level
    
    def is_overstocked(self) -> bool:
        """Check if product is above maximum stock level"""
        if self.max_stock_level is None:
            return False
        
        stock_levels = self.get_stock_levels()
        return stock_levels['available_stock'] >= self.max_stock_level
