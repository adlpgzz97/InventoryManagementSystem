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
                 barcode: str = None, dimensions: str = None, weight: float = None,
                 picture_url: str = None, batch_tracked: bool = False,
                 created_at: datetime = None):
        self.id = id
        self.name = name
        self.description = description
        self.sku = sku
        self.barcode = barcode
        self.dimensions = dimensions
        self.weight = weight
        self.picture_url = picture_url
        self.batch_tracked = batch_tracked
        self.created_at = created_at
    
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
            dimensions=data.get('dimensions'),
            weight=data.get('weight'),
            picture_url=data.get('picture_url'),
            batch_tracked=data.get('batch_tracked', False),
            created_at=data.get('created_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'sku': self.sku,
            'barcode': self.barcode,
            'dimensions': self.dimensions,
            'weight': self.weight,
            'picture_url': self.picture_url,
            'batch_tracked': self.batch_tracked,
            'created_at': self.created_at
        }
    
    @classmethod
    def get_by_id(cls, product_id: str) -> Optional['Product']:
        """Get product by ID"""
        logger.info(f"Product.get_by_id called with product_id: {product_id}")
        logger.info(f"Product ID type: {type(product_id)}")
        try:
            result = execute_query(
                """
                SELECT id, name, description, sku, barcode, dimensions, weight,
                       picture_url, batch_tracked, created_at
                FROM products WHERE id = %s
                """,
                (product_id,),
                fetch_one=True
            )
            
            if result:
                logger.info(f"Product found: {result}")
                return cls.from_dict(result)
            logger.warning(f"No product found for ID: {product_id}")
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
                SELECT id, name, description, sku, barcode, dimensions, weight,
                       picture_url, batch_tracked, created_at
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
                SELECT id, name, description, sku, barcode, dimensions, weight,
                       picture_url, batch_tracked, created_at
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
                SELECT id, name, description, sku, barcode, dimensions, weight,
                       picture_url, batch_tracked, created_at
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
               barcode: str = None, dimensions: str = None, weight: float = None,
               picture_url: str = None, batch_tracked: bool = False) -> Optional['Product']:
        """Create a new product"""
        try:
            result = execute_query(
                """
                INSERT INTO products (name, description, sku, barcode, dimensions, weight,
                                    picture_url, batch_tracked)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, sku, barcode, dimensions, weight,
                          picture_url, batch_tracked, created_at
                """,
                (name, description, sku, barcode, dimensions, weight,
                 picture_url, batch_tracked),
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
                SET {', '.join(fields)}
                WHERE id = %s
                RETURNING id
            """
            
            result = execute_query(query, tuple(values), fetch_one=True)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error updating product {self.id}: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete the product"""
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
    
    def get_stock_levels(self) -> Dict[str, int]:
        """Get current stock levels for this product"""
        try:
            from models.stock import StockItem
            
            stock_items = StockItem.get_by_product(self.id)
            
            total_on_hand = sum(item.on_hand for item in stock_items)
            total_reserved = sum(item.qty_reserved for item in stock_items)
            total_available = total_on_hand - total_reserved
            
            return {
                'total_on_hand': total_on_hand,
                'total_reserved': total_reserved,
                'total_available': total_available,
                'stock_items_count': len(stock_items)
            }
            
        except Exception as e:
            logger.error(f"Error getting stock levels for product {self.id}: {e}")
            return {
                'total_on_hand': 0,
                'total_reserved': 0,
                'total_available': 0,
                'stock_items_count': 0
            }
    
    @property
    def available_stock(self) -> int:
        """Get available stock for this product"""
        stock_levels = self.get_stock_levels()
        return stock_levels['total_available']
    
    @property
    def total_stock(self) -> int:
        """Get total stock for this product"""
        stock_levels = self.get_stock_levels()
        return stock_levels['total_on_hand']
    
    @property
    def reserved_stock(self) -> int:
        """Get reserved stock for this product"""
        stock_levels = self.get_stock_levels()
        return stock_levels['total_reserved']
    
    def is_low_stock(self) -> bool:
        """Check if product is low on stock (placeholder - no min_stock_level in schema)"""
        # Since min_stock_level doesn't exist in schema, we'll use a default threshold
        stock_levels = self.get_stock_levels()
        return stock_levels['total_available'] <= 5  # Default low stock threshold
    
    def is_overstocked(self) -> bool:
        """Check if product is overstocked (placeholder - no max_stock_level in schema)"""
        # Since max_stock_level doesn't exist in schema, we'll use a default threshold
        stock_levels = self.get_stock_levels()
        return stock_levels['total_available'] >= 100  # Default overstock threshold
