"""
Warehouse model for Inventory Management System
Handles warehouse locations, bins, and location hierarchy
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from utils.database import execute_query

# Configure logging
logger = logging.getLogger(__name__)


class Warehouse:
    """Warehouse model for inventory management"""
    
    def __init__(self, id: str, name: str, description: str = None, address: str = None,
                 contact_person: str = None, contact_email: str = None, contact_phone: str = None,
                 created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        self.name = name
        self.description = description
        self.address = address
        self.contact_person = contact_person
        self.contact_email = contact_email
        self.contact_phone = contact_phone
        self.created_at = created_at
        self.updated_at = updated_at
    
    def __repr__(self):
        return f"<Warehouse {self.name} (ID: {self.id})>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Warehouse':
        """Create Warehouse instance from dictionary"""
        return cls(
            id=str(data['id']),
            name=data['name'],
            description=data.get('description'),
            address=data.get('address'),
            contact_person=data.get('contact_person'),
            contact_email=data.get('contact_email'),
            contact_phone=data.get('contact_phone'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert warehouse to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'address': self.address,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def get_by_id(cls, warehouse_id: str) -> Optional['Warehouse']:
        """Get warehouse by ID"""
        try:
            result = execute_query(
                """
                SELECT id, name, description, address, contact_person,
                       contact_email, contact_phone, created_at, updated_at
                FROM warehouses WHERE id = %s
                """,
                (warehouse_id,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting warehouse by ID {warehouse_id}: {e}")
            return None
    
    @classmethod
    def get_all(cls) -> List['Warehouse']:
        """Get all warehouses"""
        try:
            results = execute_query(
                """
                SELECT id, name, description, address, contact_person,
                       contact_email, contact_phone, created_at, updated_at
                FROM warehouses
                ORDER BY name
                """,
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting all warehouses: {e}")
            return []
    
    @classmethod
    def create(cls, name: str, description: str = None, address: str = None,
               contact_person: str = None, contact_email: str = None,
               contact_phone: str = None) -> Optional['Warehouse']:
        """Create a new warehouse"""
        try:
            result = execute_query(
                """
                INSERT INTO warehouses (name, description, address, contact_person,
                                     contact_email, contact_phone)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, address, contact_person,
                          contact_email, contact_phone, created_at, updated_at
                """,
                (name, description, address, contact_person, contact_email, contact_phone),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating warehouse {name}: {e}")
            return None
    
    def update(self, **kwargs) -> bool:
        """Update warehouse attributes"""
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
                UPDATE warehouses 
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
            logger.error(f"Error updating warehouse {self.id}: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete warehouse"""
        try:
            result = execute_query(
                "DELETE FROM warehouses WHERE id = %s RETURNING id",
                (self.id,),
                fetch_one=True
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error deleting warehouse {self.id}: {e}")
            return False
    
    def get_locations(self) -> List['Location']:
        """Get all locations in this warehouse"""
        return Location.get_by_warehouse(self.id)
    
    def get_bins(self) -> List['Bin']:
        """Get all bins in this warehouse"""
        return Bin.get_by_warehouse(self.id)


class Location:
    """Location model for warehouse locations"""
    
    def __init__(self, id: str, warehouse_id: str, location_code: str, name: str,
                 description: str = None, parent_location_id: str = None,
                 created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        self.warehouse_id = warehouse_id
        self.location_code = location_code
        self.name = name
        self.description = description
        self.parent_location_id = parent_location_id
        self.created_at = created_at
        self.updated_at = updated_at
    
    def __repr__(self):
        return f"<Location {self.location_code} (ID: {self.id})>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Location':
        """Create Location instance from dictionary"""
        return cls(
            id=str(data['id']),
            warehouse_id=str(data['warehouse_id']),
            location_code=data['location_code'],
            name=data['name'],
            description=data.get('description'),
            parent_location_id=data.get('parent_location_id'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    @classmethod
    def get_by_id(cls, location_id: str) -> Optional['Location']:
        """Get location by ID"""
        try:
            result = execute_query(
                """
                SELECT id, warehouse_id, location_code, name, description,
                       parent_location_id, created_at, updated_at
                FROM locations WHERE id = %s
                """,
                (location_id,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting location by ID {location_id}: {e}")
            return None
    
    @classmethod
    def get_by_code(cls, location_code: str) -> Optional['Location']:
        """Get location by code"""
        try:
            result = execute_query(
                """
                SELECT id, warehouse_id, location_code, name, description,
                       parent_location_id, created_at, updated_at
                FROM locations WHERE location_code = %s
                """,
                (location_code,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting location by code {location_code}: {e}")
            return None
    
    @classmethod
    def get_by_warehouse(cls, warehouse_id: str) -> List['Location']:
        """Get all locations in a warehouse"""
        try:
            results = execute_query(
                """
                SELECT id, warehouse_id, location_code, name, description,
                       parent_location_id, created_at, updated_at
                FROM locations 
                WHERE warehouse_id = %s
                ORDER BY location_code
                """,
                (warehouse_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting locations for warehouse {warehouse_id}: {e}")
            return []
    
    @classmethod
    def create(cls, warehouse_id: str, location_code: str, name: str,
               description: str = None, parent_location_id: str = None) -> Optional['Location']:
        """Create a new location"""
        try:
            result = execute_query(
                """
                INSERT INTO locations (warehouse_id, location_code, name, description,
                                     parent_location_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, warehouse_id, location_code, name, description,
                          parent_location_id, created_at, updated_at
                """,
                (warehouse_id, location_code, name, description, parent_location_id),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating location {location_code}: {e}")
            return None
    
    def get_bins(self) -> List['Bin']:
        """Get all bins in this location"""
        return Bin.get_by_location(self.id)
    
    def get_child_locations(self) -> List['Location']:
        """Get child locations"""
        try:
            results = execute_query(
                """
                SELECT id, warehouse_id, location_code, name, description,
                       parent_location_id, created_at, updated_at
                FROM locations 
                WHERE parent_location_id = %s
                ORDER BY location_code
                """,
                (self.id,),
                fetch_all=True
            )
            
            return [Location.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting child locations for {self.id}: {e}")
            return []


class Bin:
    """Bin model for warehouse storage bins"""
    
    def __init__(self, id: str, bin_code: str, location_id: str = None, description: str = None,
                 capacity: int = None, created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        self.bin_code = bin_code
        self.location_id = location_id
        self.description = description
        self.capacity = capacity
        self.created_at = created_at
        self.updated_at = updated_at
    
    def __repr__(self):
        return f"<Bin {self.bin_code} (ID: {self.id})>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bin':
        """Create Bin instance from dictionary"""
        return cls(
            id=str(data['id']),
            bin_code=data['bin_code'],
            location_id=data.get('location_id'),
            description=data.get('description'),
            capacity=data.get('capacity'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    @classmethod
    def get_by_id(cls, bin_id: str) -> Optional['Bin']:
        """Get bin by ID"""
        try:
            result = execute_query(
                """
                SELECT id, bin_code, location_id, description, capacity,
                       created_at, updated_at
                FROM bins WHERE id = %s
                """,
                (bin_id,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting bin by ID {bin_id}: {e}")
            return None
    
    @classmethod
    def get_by_code(cls, bin_code: str) -> Optional['Bin']:
        """Get bin by code"""
        try:
            result = execute_query(
                """
                SELECT id, bin_code, location_id, description, capacity,
                       created_at, updated_at
                FROM bins WHERE bin_code = %s
                """,
                (bin_code,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting bin by code {bin_code}: {e}")
            return None
    
    @classmethod
    def get_by_location(cls, location_id: str) -> List['Bin']:
        """Get all bins in a location"""
        try:
            results = execute_query(
                """
                SELECT id, bin_code, location_id, description, capacity,
                       created_at, updated_at
                FROM bins 
                WHERE location_id = %s
                ORDER BY bin_code
                """,
                (location_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting bins for location {location_id}: {e}")
            return []
    
    @classmethod
    def get_by_warehouse(cls, warehouse_id: str) -> List['Bin']:
        """Get all bins in a warehouse"""
        try:
            results = execute_query(
                """
                SELECT b.id, b.bin_code, b.location_id, b.description, b.capacity,
                       b.created_at, b.updated_at
                FROM bins b
                JOIN locations l ON b.location_id = l.id
                WHERE l.warehouse_id = %s
                ORDER BY b.bin_code
                """,
                (warehouse_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting bins for warehouse {warehouse_id}: {e}")
            return []
    
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> List['Bin']:
        """Get all bins with optional pagination"""
        try:
            query = """
                SELECT id, bin_code, location_id, description, capacity,
                       created_at, updated_at
                FROM bins
                ORDER BY bin_code
            """
            
            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
            
            results = execute_query(query, fetch_all=True)
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting all bins: {e}")
            return []
    
    @classmethod
    def create(cls, bin_code: str, location_id: str = None, description: str = None,
               capacity: int = None) -> Optional['Bin']:
        """Create a new bin"""
        try:
            result = execute_query(
                """
                INSERT INTO bins (bin_code, location_id, description, capacity)
                VALUES (%s, %s, %s, %s)
                RETURNING id, bin_code, location_id, description, capacity,
                          created_at, updated_at
                """,
                (bin_code, location_id, description, capacity),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating bin {bin_code}: {e}")
            return None
    
    def update_location(self, location_id: str) -> bool:
        """Update bin location"""
        try:
            result = execute_query(
                """
                UPDATE bins 
                SET location_id = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                (location_id, self.id),
                fetch_one=True
            )
            
            if result:
                self.location_id = location_id
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating bin location {self.id}: {e}")
            return False
    
    def get_stock_items(self) -> List['StockItem']:
        """Get all stock items in this bin"""
        from .stock import StockItem
        return StockItem.get_by_bin(self.id)
    
    def get_available_capacity(self) -> Optional[int]:
        """Get available capacity if capacity is set"""
        if self.capacity is None:
            return None
        
        stock_items = self.get_stock_items()
        used_capacity = sum(item.on_hand for item in stock_items)
        return max(0, self.capacity - used_capacity)
