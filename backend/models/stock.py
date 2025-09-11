"""
Stock model for Inventory Management System
Pure data container with basic CRUD operations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from backend.models.base_model import BaseModel
from backend.utils.database import execute_query

logger = logging.getLogger(__name__)


class StockItem(BaseModel):
    """Stock item model - data container only"""
    
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
        """Calculate available stock (on_hand - reserved) - basic computed property"""
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
            'reserved': self.qty_reserved,
            'available_stock': self.available_stock,
            'batch_id': self.batch_id,
            'expiry_date': self.expiry_date,
            'created_at': self.created_at
        }
    
    @classmethod
    def get_by_id(cls, stock_id: str) -> Optional['StockItem']:
        """Get stock item by ID - basic CRUD operation"""
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
        """Get stock item by product and bin - basic CRUD operation"""
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
            logger.error(f"Error getting stock item by product and bin: {e}")
            return None
    
    @classmethod
    def get_by_product(cls, product_id: str) -> List['StockItem']:
        """Get all stock items for a product - basic CRUD operation"""
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
            logger.error(f"Error getting stock items by product: {e}")
            return []
    
    @classmethod
    def get_by_bin(cls, bin_id: str) -> List['StockItem']:
        """Get all stock items in a bin - basic CRUD operation"""
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
            logger.error(f"Error getting stock items by bin: {e}")
            return []
    
    @classmethod
    def get_all_with_locations(cls) -> List[Dict[str, Any]]:
        """Get all stock items with location and product information"""
        try:
            results = execute_query(
                """
                SELECT 
                    si.id, si.product_id, si.bin_id, si.on_hand, si.qty_reserved,
                    si.batch_id, si.expiry_date, si.created_at,
                    p.name as product_name, p.sku as product_sku,
                    b.code as bin_code,
                    l.full_code as location_code,
                    w.id as warehouse_id,
                    w.name as warehouse_name
                FROM stock_items si
                JOIN products p ON si.product_id = p.id
                JOIN bins b ON si.bin_id = b.id
                LEFT JOIN locations l ON b.location_id = l.id
                LEFT JOIN warehouses w ON l.warehouse_id = w.id
                ORDER BY p.name, b.code
                """,
                fetch_all=True
            )
            
            return results if results else []
            
        except Exception as e:
            logger.error(f"Error getting stock items with locations: {e}")
            return []
    
    @classmethod
    def get_by_batch(cls, batch_id: str) -> List['StockItem']:
        """Get all stock items for a batch - basic CRUD operation"""
        try:
            results = execute_query(
                """
                SELECT id, product_id, bin_id, on_hand, qty_reserved,
                       batch_id, expiry_date, created_at
                FROM stock_items 
                WHERE batch_id = %s
                ORDER BY created_at DESC
                """,
                (batch_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting stock items by batch: {e}")
            return []
    
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> List['StockItem']:
        """Get all stock items with optional pagination - basic CRUD operation"""
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
    def create(cls, product_id: str, bin_id: str, on_hand: int = 0,
               qty_reserved: int = 0, batch_id: str = None,
               expiry_date: datetime = None) -> Optional['StockItem']:
        """Create a new stock item - basic CRUD operation"""
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
    
    def update(self, **kwargs) -> bool:
        """Update stock item attributes - basic CRUD operation"""
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
                UPDATE stock_items 
                SET {', '.join(fields)}
                WHERE id = %s
                RETURNING id
            """
            
            result = execute_query(query, tuple(values), fetch_one=True)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error updating stock item {self.id}: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete the stock item - basic CRUD operation"""
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

    def update_stock(self, on_hand: int = None, qty_reserved: int = None) -> bool:
        """Update on_hand and/or qty_reserved safely for this stock item."""
        try:
            fields = []
            params = []
            if on_hand is not None:
                on_hand = max(0, int(on_hand))
                fields.append("on_hand = %s")
                params.append(on_hand)
            if qty_reserved is not None:
                qty_reserved = max(0, int(qty_reserved))
                fields.append("qty_reserved = %s")
                params.append(qty_reserved)
            if not fields:
                return False
            params.append(self.id)
            query = f"""
                UPDATE stock_items
                SET {', '.join(fields)}
                WHERE id = %s
                RETURNING id, on_hand, qty_reserved
            """
            result = execute_query(query, tuple(params), fetch_one=True)
            if result:
                # Refresh in-memory values
                self.on_hand = result.get('on_hand', self.on_hand)
                self.qty_reserved = result.get('qty_reserved', self.qty_reserved)
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating stock quantities for {self.id}: {e}")
            return False


class StockTransaction(BaseModel):
    """Stock transaction model - data container only"""
    
    def __init__(self, id: str, stock_item_id: str, transaction_type: str,
                 quantity_change: int, quantity_before: int, quantity_after: int,
                 user_id: str = None, notes: str = None, reference_id: str = None,
                 created_at: datetime = None):
        self.id = id
        self.stock_item_id = stock_item_id
        self.transaction_type = transaction_type
        self.quantity_change = quantity_change
        self.quantity_before = quantity_before
        self.quantity_after = quantity_after
        self.user_id = user_id
        self.notes = notes
        self.reference_id = reference_id
        self.created_at = created_at
    
    def __repr__(self):
        return f"<StockTransaction {self.transaction_type} (ID: {self.id})>"
    
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
            user_id=str(data['user_id']),
            notes=data.get('notes'),
            reference_id=data.get('reference_id'),
            created_at=data.get('created_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stock transaction to dictionary"""
        return {
            'id': self.id,
            'stock_item_id': self.stock_item_id,
            'transaction_type': self.transaction_type,
            'quantity_change': self.quantity_change,
            'quantity_before': self.quantity_before,
            'quantity_after': self.quantity_after,
            'user_id': self.user_id,
            'notes': self.notes,
            'reference_id': self.reference_id,
            'created_at': self.created_at
        }
    
    @classmethod
    def get_by_id(cls, transaction_id: str) -> Optional['StockTransaction']:
        """Get transaction by ID - basic CRUD operation"""
        try:
            result = execute_query(
                """
                SELECT id, stock_item_id, transaction_type, quantity_change,
                       quantity_before, quantity_after, user_id, notes, reference_id, created_at
                FROM stock_transactions WHERE id = %s
                """,
                (transaction_id,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting transaction by ID {transaction_id}: {e}")
            return None
    
    @classmethod
    def get_by_stock_item(cls, stock_item_id: str) -> List['StockTransaction']:
        """Get all transactions for a stock item - basic CRUD operation"""
        try:
            results = execute_query(
                """
                SELECT id, stock_item_id, transaction_type, quantity_change,
                       quantity_before, quantity_after, user_id, notes, reference_id, created_at
                FROM stock_transactions 
                WHERE stock_item_id = %s
                ORDER BY created_at DESC
                """,
                (stock_item_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting transactions by stock item: {e}")
            return []
    
    @classmethod
    def get_by_reference(cls, reference_id: str) -> List['StockTransaction']:
        """Get all transactions for a reference ID - basic CRUD operation"""
        try:
            results = execute_query(
                """
                SELECT id, stock_item_id, transaction_type, quantity_change,
                       quantity_before, quantity_after, user_id, notes, reference_id, created_at
                FROM stock_transactions 
                WHERE reference_id = %s
                ORDER BY created_at ASC
                """,
                (reference_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting transactions by reference: {e}")
            return []
    
    @classmethod
    def create(cls, stock_item_id: str, transaction_type: str,
               quantity_change: int, quantity_before: int, quantity_after: int,
               user_id: str, notes: str = None, reference_id: str = None) -> Optional['StockTransaction']:
        """Create a new transaction - basic CRUD operation"""
        try:
            result = execute_query(
                """
                INSERT INTO stock_transactions (stock_item_id, transaction_type, quantity_change,
                                              quantity_before, quantity_after, user_id, notes, reference_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, stock_item_id, transaction_type, quantity_change,
                          quantity_before, quantity_after, user_id, notes, reference_id, created_at
                """,
                (stock_item_id, transaction_type, quantity_change, quantity_before,
                 quantity_after, user_id, notes, reference_id),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return None
