"""
Stock model for Inventory Management System
Handles stock items, inventory tracking, and stock operations
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from utils.database import execute_query

# Configure logging
logger = logging.getLogger(__name__)


class StockItem:
    """Stock item model for inventory management"""
    
    def __init__(self, id: str, product_id: str, bin_id: str, on_hand: int = 0,
                 qty_reserved: int = 0, batch_id: str = None, expiry_date: datetime = None,
                 created_at: datetime = None):
        self.id = id
        self.product_id = product_id
        self.bin_id = bin_id
        self.on_hand = on_hand
        self.qty_reserved = qty_reserved
        self.batch_id = batch_id
        self.expiry_date = expiry_date
        self.created_at = created_at
    
    def __repr__(self):
        return f"<StockItem ID: {self.id}, Product: {self.product_id}, Bin: {self.bin_id}>"
    
    @property
    def available_stock(self) -> int:
        """Calculate available stock (on_hand - reserved)"""
        return max(0, self.on_hand - self.qty_reserved)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StockItem':
        """Create StockItem instance from dictionary"""
        return cls(
            id=str(data['id']),
            product_id=str(data['product_id']),
            bin_id=str(data['bin_id']),
            on_hand=data.get('on_hand', 0),
            qty_reserved=data.get('qty_reserved', 0),
            batch_id=data.get('batch_id'),
            expiry_date=data.get('expiry_date'),
            created_at=data.get('created_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stock item to dictionary"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'bin_id': self.bin_id,
            'on_hand': self.on_hand,
            'qty_reserved': self.qty_reserved,
            'available_stock': self.available_stock,
            'batch_id': self.batch_id,
            'expiry_date': self.expiry_date,
            'created_at': self.created_at
        }
    
    @classmethod
    def get_by_id(cls, stock_id: str) -> Optional['StockItem']:
        """Get stock item by ID"""
        try:
            result = execute_query(
                """
                SELECT id, product_id, bin_id, on_hand, qty_reserved,
                       batch_id, expiry_date, created_at
                FROM stock_items WHERE id = %s
                """,
                (stock_id,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting stock item by ID {stock_id}: {e}")
            return None
    
    @classmethod
    def get_by_product_and_bin(cls, product_id: str, bin_id: str) -> Optional['StockItem']:
        """Get stock item by product and bin"""
        try:
            result = execute_query(
                """
                SELECT id, product_id, bin_id, on_hand, qty_reserved,
                       batch_id, expiry_date, created_at
                FROM stock_items 
                WHERE product_id = %s AND bin_id = %s
                """,
                (product_id, bin_id),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting stock item by product {product_id} and bin {bin_id}: {e}")
            return None
    
    @classmethod
    def get_by_product(cls, product_id: str) -> List['StockItem']:
        """Get all stock items for a product"""
        try:
            results = execute_query(
                """
                SELECT id, product_id, bin_id, on_hand, qty_reserved,
                       batch_id, expiry_date, created_at
                FROM stock_items 
                WHERE product_id = %s
                ORDER BY created_at DESC
                """,
                (product_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting stock items for product {product_id}: {e}")
            return []
    
    @classmethod
    def get_by_bin(cls, bin_id: str) -> List['StockItem']:
        """Get all stock items in a bin"""
        try:
            results = execute_query(
                """
                SELECT id, product_id, bin_id, on_hand, qty_reserved,
                       batch_id, expiry_date, created_at
                FROM stock_items 
                WHERE bin_id = %s
                ORDER BY created_at DESC
                """,
                (bin_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting stock items for bin {bin_id}: {e}")
            return []
    
    @classmethod
    def create(cls, product_id: str, bin_id: str, on_hand: int = 0,
               qty_reserved: int = 0, batch_id: str = None,
               expiry_date: datetime = None) -> Optional['StockItem']:
        """Create a new stock item"""
        try:
            result = execute_query(
                """
                INSERT INTO stock_items (product_id, bin_id, on_hand, qty_reserved,
                                       batch_id, expiry_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, product_id, bin_id, on_hand, qty_reserved,
                          batch_id, expiry_date, created_at
                """,
                (product_id, bin_id, on_hand, qty_reserved, batch_id, expiry_date),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating stock item: {e}")
            return None
    
    def update_stock(self, on_hand: int = None, qty_reserved: int = None) -> bool:
        """Update stock quantities"""
        try:
            updates = []
            values = []
            
            if on_hand is not None:
                updates.append("on_hand = %s")
                values.append(on_hand)
            
            if qty_reserved is not None:
                updates.append("qty_reserved = %s")
                values.append(qty_reserved)
            
            if not updates:
                return False
            
            values.append(self.id)
            
            query = f"""
                UPDATE stock_items 
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id
            """
            
            result = execute_query(query, tuple(values), fetch_one=True)
            
            if result:
                # Update instance attributes
                if on_hand is not None:
                    self.on_hand = on_hand
                if qty_reserved is not None:
                    self.qty_reserved = qty_reserved
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating stock item {self.id}: {e}")
            return False
    
    def reserve_stock(self, quantity: int) -> bool:
        """Reserve stock quantity"""
        if quantity > self.available_stock:
            return False
        
        return self.update_stock(qty_reserved=self.qty_reserved + quantity)
    
    def release_reserved_stock(self, quantity: int) -> bool:
        """Release reserved stock quantity"""
        if quantity > self.qty_reserved:
            return False
        
        return self.update_stock(qty_reserved=self.qty_reserved - quantity)
    
    def add_stock(self, quantity: int) -> bool:
        """Add stock quantity"""
        return self.update_stock(on_hand=self.on_hand + quantity)
    
    def remove_stock(self, quantity: int) -> bool:
        """Remove stock quantity"""
        if quantity > self.available_stock:
            return False
        
        return self.update_stock(on_hand=self.on_hand - quantity)
    
    def delete(self) -> bool:
        """Delete stock item"""
        try:
            result = execute_query(
                "DELETE FROM stock_items WHERE id = %s RETURNING id",
                (self.id,),
                fetch_one=True
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error deleting stock item {self.id}: {e}")
            return False
    
    def is_expired(self) -> bool:
        """Check if stock item is expired"""
        if not self.expiry_date:
            return False
        
        return datetime.now().date() > self.expiry_date
    
    def days_until_expiry(self) -> Optional[int]:
        """Get days until expiry"""
        if not self.expiry_date:
            return None
        
        delta = self.expiry_date - datetime.now().date()
        return delta.days
    
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> List['StockItem']:
        """Get all stock items with optional pagination"""
        try:
            query = """
                SELECT id, product_id, bin_id, on_hand, qty_reserved,
                       batch_id, expiry_date, created_at
                FROM stock_items
                ORDER BY created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
            
            results = execute_query(query, fetch_all=True)
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting all stock items: {e}")
            return []

    @classmethod
    def get_all_with_locations(cls, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """Get all stock items with full location hierarchy"""
        try:
            query = """
                SELECT 
                    si.id, si.product_id, si.bin_id, si.on_hand, si.qty_reserved,
                    si.batch_id, si.expiry_date, si.created_at,
                    p.name as product_name, p.sku as product_sku,
                    b.code as bin_code,
                    l.full_code as location_code,
                    w.id as warehouse_id, w.name as warehouse_name, w.code as warehouse_code
                FROM stock_items si
                JOIN products p ON si.product_id = p.id
                JOIN bins b ON si.bin_id = b.id
                LEFT JOIN locations l ON b.location_id = l.id
                LEFT JOIN warehouses w ON l.warehouse_id = w.id
                ORDER BY si.created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
            
            results = execute_query(query, fetch_all=True)
            
            # Convert to list of dictionaries with enhanced data
            stock_items = []
            for result in results:
                stock_item = {
                    'id': result['id'],
                    'product_id': result['product_id'],
                    'bin_id': result['bin_id'],
                    'on_hand': result['on_hand'],
                    'qty_reserved': result['qty_reserved'],
                    'available_stock': result['on_hand'] - result['qty_reserved'],
                    'batch_id': result['batch_id'],
                    'expiry_date': result['expiry_date'],
                    'created_at': result['created_at'],
                    'product': {
                        'name': result['product_name'],
                        'sku': result['product_sku']
                    },
                    'bin': {
                        'code': result['bin_code']
                    },
                    'location': {
                        'code': result['location_code']
                    },
                    'warehouse': {
                        'id': result['warehouse_id'],
                        'name': result['warehouse_name'],
                        'code': result['warehouse_code']
                    },
                    'warehouse_id': result['warehouse_id']
                }
                stock_items.append(stock_item)
            
            return stock_items
            
        except Exception as e:
            logger.error(f"Error getting stock items with locations: {e}")
            return []


class StockTransaction:
    """Stock transaction model for tracking stock movements"""
    
    def __init__(self, id: str, stock_item_id: str, transaction_type: str,
                 quantity_change: int, quantity_before: int, quantity_after: int,
                 notes: str = None, user_id: str = None, created_at: datetime = None):
        self.id = id
        self.stock_item_id = stock_item_id
        self.transaction_type = transaction_type
        self.quantity_change = quantity_change
        self.quantity_before = quantity_before
        self.quantity_after = quantity_after
        self.notes = notes
        self.user_id = user_id
        self.created_at = created_at
    
    def __repr__(self):
        return f"<StockTransaction {self.transaction_type} (ID: {self.id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stock transaction to dictionary"""
        return {
            'id': self.id,
            'stock_item_id': self.stock_item_id,
            'transaction_type': self.transaction_type,
            'quantity_change': self.quantity_change,
            'quantity_before': self.quantity_before,
            'quantity_after': self.quantity_after,
            'notes': self.notes,
            'user_id': self.user_id,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StockTransaction':
        """Create StockTransaction instance from dictionary"""
        return cls(
            id=str(data['id']),
            stock_item_id=str(data['stock_item_id']),
            transaction_type=data['transaction_type'],
            quantity_change=data['quantity_change'],
            quantity_before=data['quantity_before'],
            quantity_after=data['quantity_after'],
            notes=data.get('notes'),
            user_id=data.get('user_id'),
            created_at=data.get('created_at')
        )
    
    @classmethod
    def create(cls, stock_item_id: str, transaction_type: str, quantity_change: int,
               quantity_before: int, quantity_after: int, notes: str = None,
               user_id: str = None) -> Optional['StockTransaction']:
        """Create a new stock transaction"""
        try:
            result = execute_query(
                """
                INSERT INTO stock_transactions 
                (stock_item_id, transaction_type, quantity_change, quantity_before,
                 quantity_after, notes, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, stock_item_id, transaction_type, quantity_change,
                          quantity_before, quantity_after, notes, user_id, created_at
                """,
                (stock_item_id, transaction_type, quantity_change, quantity_before,
                 quantity_after, notes, user_id),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating stock transaction: {e}")
            return None
    
    @classmethod
    def get_by_stock_item(cls, stock_item_id: str, limit: int = None) -> List['StockTransaction']:
        """Get transactions for a stock item"""
        try:
            query = """
                SELECT id, stock_item_id, transaction_type, quantity_change,
                       quantity_before, quantity_after, notes, user_id, created_at
                FROM stock_transactions 
                WHERE stock_item_id = %s
                ORDER BY created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            results = execute_query(query, (stock_item_id,), fetch_all=True)
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting transactions for stock item {stock_item_id}: {e}")
            return []
