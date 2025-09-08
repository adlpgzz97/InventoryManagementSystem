"""
Warehouse model for Inventory Management System
Pure data container with basic CRUD operations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from backend.models.base_model import BaseModel
from backend.utils.database import execute_query

logger = logging.getLogger(__name__)


class Warehouse(BaseModel):
    """Warehouse model - data container only"""
    
    def __init__(self, id: str, name: str, address: str = None, code: str = None):
        self.id = id
        self.name = name
        self.address = address
        self.code = code
    
    def __repr__(self):
        return f"<Warehouse {self.name} (ID: {self.id})>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Warehouse':
        """Create Warehouse instance from dictionary"""
        return cls(
            id=str(data['id']),
            name=data['name'],
            address=data.get('address'),
            code=data.get('code')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert warehouse to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'code': self.code
        }
    
    @classmethod
    def get_by_id(cls, warehouse_id: str) -> Optional['Warehouse']:
        """Get warehouse by ID - basic CRUD operation"""
        try:
            result = execute_query(
                """
                SELECT id, name, address, code
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
        """Get all warehouses - basic CRUD operation"""
        try:
            results = execute_query(
                """
                SELECT id, name, address, code
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
    def create(cls, name: str, address: str = None, code: str = None) -> Optional['Warehouse']:
        """Create a new warehouse - basic CRUD operation"""
        try:
            result = execute_query(
                """
                INSERT INTO warehouses (name, address, code)
                VALUES (%s, %s, %s)
                RETURNING id, name, address, code
                """,
                (name, address, code),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating warehouse: {e}")
            return None
    
    def update(self, **kwargs) -> bool:
        """Update warehouse attributes - basic CRUD operation"""
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
                SET {', '.join(fields)}
                WHERE id = %s
                RETURNING id
            """
            
            result = execute_query(query, tuple(values), fetch_one=True)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error updating warehouse {self.id}: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete the warehouse - basic CRUD operation"""
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


class Location:
    """Location model - data container only"""
    
    def __init__(self, id: str, warehouse_id: str, full_code: str = None):
        self.id = id
        self.warehouse_id = warehouse_id
        self.full_code = full_code
    
    def __repr__(self):
        return f"<Location {self.full_code} (ID: {self.id})>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Location':
        """Create Location instance from dictionary"""
        return cls(
            id=str(data['id']),
            warehouse_id=str(data['warehouse_id']),
            full_code=data.get('full_code')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert location to dictionary"""
        return {
            'id': self.id,
            'warehouse_id': self.warehouse_id,
            'full_code': self.full_code
        }
    
    @classmethod
    def get_by_id(cls, location_id: str) -> Optional['Location']:
        """Get location by ID - basic CRUD operation"""
        try:
            result = execute_query(
                """
                SELECT id, warehouse_id, full_code
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
        """Get location by code - basic CRUD operation"""
        try:
            result = execute_query(
                """
                SELECT id, warehouse_id, full_code
                FROM locations WHERE full_code = %s
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
        """Get all locations in a warehouse - basic CRUD operation"""
        try:
            results = execute_query(
                """
                SELECT id, warehouse_id, full_code
                FROM locations 
                WHERE warehouse_id = %s
                ORDER BY full_code
                """,
                (warehouse_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting locations by warehouse: {e}")
            return []
    
    @classmethod
    def search(cls, search_term: str) -> List['Location']:
        """Search locations by code or name - basic CRUD operation"""
        try:
            search_pattern = f"%{search_term}%"
            
            results = execute_query(
                """
                SELECT id, warehouse_id, full_code
                FROM locations
                WHERE full_code ILIKE %s
                ORDER BY full_code
                """,
                (search_pattern,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error searching locations: {e}")
            return []
    
    @classmethod
    def create(cls, warehouse_id: str, code: str, name: str, 
               description: str = None, full_code: str = None) -> Optional['Location']:
        """Create a new location - basic CRUD operation"""
        try:
            result = execute_query(
                """
                INSERT INTO locations (warehouse_id, code, name, description, full_code)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, warehouse_id, code, name, description, full_code
                """,
                (warehouse_id, code, name, description, full_code),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating location: {e}")
            return None
    
    def update(self, **kwargs) -> bool:
        """Update location attributes - basic CRUD operation"""
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
                UPDATE locations 
                SET {', '.join(fields)}
                WHERE id = %s
                RETURNING id
            """
            
            result = execute_query(query, tuple(values), fetch_one=True)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error updating location {self.id}: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete the location - basic CRUD operation"""
        try:
            result = execute_query(
                "DELETE FROM locations WHERE id = %s RETURNING id",
                (self.id,),
                fetch_one=True
            )
            return result is not None
            
        except Exception as e:
            logger.error(f"Error deleting location {self.id}: {e}")
            return False


class Bin:
    """Bin model - data container only"""
    
    def __init__(self, id: str, location_id: str, code: str, created_at=None, updated_at=None):
        self.id = id
        self.location_id = location_id
        self.code = code
        self.created_at = created_at
        self.updated_at = updated_at
    
    def __repr__(self):
        return f"<Bin {self.code} (ID: {self.id})>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bin':
        """Create Bin instance from dictionary"""
        return cls(
            id=str(data['id']),
            location_id=str(data['location_id']),
            code=data['code'],
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert bin to dictionary"""
        return {
            'id': self.id,
            'location_id': self.location_id,
            'code': self.code,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def get_by_id(cls, bin_id: str) -> Optional['Bin']:
        """Get bin by ID - basic CRUD operation"""
        try:
            result = execute_query(
                """
                SELECT id, location_id, code, created_at, updated_at
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
        """Get bin by code - basic CRUD operation"""
        try:
            result = execute_query(
                """
                SELECT id, location_id, code, created_at, updated_at
                FROM bins WHERE code = %s
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
        """Get all bins in a location - basic CRUD operation"""
        try:
            results = execute_query(
                """
                SELECT id, location_id, code, created_at, updated_at
                FROM bins 
                WHERE location_id = %s
                ORDER BY code
                """,
                (location_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting bins by location: {e}")
            return []
    
    @classmethod
    def get_all(cls) -> List['Bin']:
        """Get all bins - basic CRUD operation"""
        try:
            results = execute_query(
                """
                SELECT id, location_id, code, created_at, updated_at
                FROM bins 
                ORDER BY code
                """,
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting bins by location: {e}")
            return []
    
    @classmethod
    def search(cls, search_term: str) -> List['Bin']:
        """Search bins by code or name - basic CRUD operation"""
        try:
            search_pattern = f"%{search_term}%"
            
            results = execute_query(
                """
                SELECT id, location_id, code, created_at, updated_at
                FROM bins
                WHERE code ILIKE %s
                ORDER BY code
                """,
                (search_pattern,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error searching bins: {e}")
            return []
    
    @classmethod
    def create(cls, location_id: str, code: str) -> Optional['Bin']:
        """Create a new bin - basic CRUD operation"""
        try:
            result = execute_query(
                """
                INSERT INTO bins (location_id, code)
                VALUES (%s, %s)
                RETURNING id, location_id, code, created_at, updated_at
                """,
                (location_id, code),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating bin: {e}")
            return None
    
    def update(self, **kwargs) -> bool:
        """Update bin attributes - basic CRUD operation"""
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
                UPDATE bins 
                SET {', '.join(fields)}
                WHERE id = %s
                RETURNING id
            """
            
            result = execute_query(query, tuple(values), fetch_one=True)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error updating bin {self.id}: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete the bin - basic CRUD operation"""
        try:
            result = execute_query(
                "DELETE FROM bins WHERE id = %s RETURNING id",
                (self.id,),
                fetch_one=True
            )
            return result is not None
            
        except Exception as e:
            logger.error(f"Error deleting bin {self.id}: {e}")
            return False