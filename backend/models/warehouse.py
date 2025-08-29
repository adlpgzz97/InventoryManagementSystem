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
        """Get warehouse by ID"""
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
        """Get all warehouses"""
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
        """Create a new warehouse"""
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
        """Delete the warehouse"""
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
    
    def get_hierarchical_locations(self) -> Dict[str, Any]:
        """Get locations organized in a hierarchical structure"""
        locations = self.get_locations()
        hierarchical = {
            'areas': {},
            'total_locations': len(locations),
            'total_bins': 0,
            'occupied_bins': 0
        }
        
        for location in locations:
            # Parse location code to extract hierarchy
            # Expected format: A1A1, B1A1, C1A1 (Warehouse+Area+Section+Rack+Level)
            full_code = location.full_code if location.full_code else ''
            
            if len(full_code) >= 4:
                # Extract warehouse code (A1A1 -> A, B1A1 -> B, C1A1 -> C)
                warehouse_code = full_code[0] if len(full_code) > 0 else 'A'
                
                # Extract area number (A1A1 -> 1, A2A1 -> 2)
                area_number = full_code[1] if len(full_code) > 1 and full_code[1].isdigit() else '1'
                area_code = f"A{area_number}"
                
                # Extract rack letter (A1A1 -> A, A1B1 -> B)
                rack_letter = full_code[2] if len(full_code) > 2 else 'A'
                rack_code = f"R{ord(rack_letter) - ord('A') + 1:02d}"
                
                # Extract level number (A1A1 -> 1, A1A2 -> 2)
                level_number = full_code[3:] if len(full_code) > 3 else '1'
                level_code = f"L{level_number}"
                
                # Initialize area if not exists
                if area_code not in hierarchical['areas']:
                    hierarchical['areas'][area_code] = {
                        'name': f'Area {area_number}',
                        'code': area_code,
                        'warehouse_code': warehouse_code,
                        'racks': {},
                        'total_locations': 0,
                        'total_bins': 0,
                        'occupied_bins': 0
                    }
                
                # Initialize rack if not exists
                if rack_code not in hierarchical['areas'][area_code]['racks']:
                    hierarchical['areas'][area_code]['racks'][rack_code] = {
                        'name': f'Rack {rack_letter}',
                        'code': rack_code,
                        'levels': {},
                        'total_locations': 0,
                        'total_bins': 0,
                        'occupied_bins': 0
                    }
                
                # Initialize level if not exists
                if level_code not in hierarchical['areas'][area_code]['racks'][rack_code]['levels']:
                    hierarchical['areas'][area_code]['racks'][rack_code]['levels'][level_code] = {
                        'name': f'Level {level_number}',
                        'code': level_code,
                        'bins': [],
                        'total_bins': 0,
                        'occupied_bins': 0
                    }
                
                # Get all bins for this location
                bins = Bin.get_by_location(location.id)
                if bins:
                    # Add each bin individually to the level
                    for bin_obj in bins:
                        bin_info = {
                            'id': bin_obj.id,
                            'code': bin_obj.code,  # Use actual bin code (e.g., B1001)
                            'full_code': location.full_code,  # Keep location code for reference
                            'location_id': location.id,
                            'bin_id': bin_obj.id,
                            'occupied': False,
                            'stock_count': 0,
                            'total_stock_quantity': 0
                        }
                        
                        # Check if this specific bin has stock
                        stock_items = bin_obj.get_stock_items()
                        if stock_items:
                            bin_info['stock_count'] = len(stock_items)
                            bin_info['total_stock_quantity'] = sum(item.on_hand for item in stock_items)
                            if any(item.on_hand > 0 for item in stock_items):
                                bin_info['occupied'] = True
                                hierarchical['occupied_bins'] += 1
                                hierarchical['areas'][area_code]['occupied_bins'] += 1
                                hierarchical['areas'][area_code]['racks'][rack_code]['occupied_bins'] += 1
                                hierarchical['areas'][area_code]['racks'][rack_code]['levels'][level_code]['occupied_bins'] += 1
                        
                        hierarchical['areas'][area_code]['racks'][rack_code]['levels'][level_code]['bins'].append(bin_info)
                        hierarchical['areas'][area_code]['racks'][rack_code]['levels'][level_code]['total_bins'] += 1
                        hierarchical['areas'][area_code]['racks'][rack_code]['total_bins'] += 1
                        hierarchical['areas'][area_code]['total_bins'] += 1
                        hierarchical['total_bins'] += 1
                else:
                    # If no bins exist for this location, create an empty location indicator
                    # BUT don't count it as a bin in the totals
                    bin_info = {
                        'id': location.id,
                        'code': 'Empty',  # Simple "Empty" indicator
                        'full_code': location.full_code,
                        'location_id': location.id,
                        'bin_id': None,
                        'occupied': False,
                        'stock_count': 0,
                        'total_stock_quantity': 0,
                        'is_empty_location': True  # Flag to identify empty locations
                    }
                    hierarchical['areas'][area_code]['racks'][rack_code]['levels'][level_code]['bins'].append(bin_info)
                    # Note: We don't increment bin counts for empty locations
                
                # Update location counts
                hierarchical['areas'][area_code]['total_locations'] += 1
                hierarchical['areas'][area_code]['racks'][rack_code]['total_locations'] += 1
        
        return hierarchical
    
    def get_bins(self) -> List['Bin']:
        """Get all bins in this warehouse"""
        return Bin.get_by_warehouse(self.id)


class Location:
    """Location model for warehouse locations"""
    
    def __init__(self, id: str, warehouse_id: str, full_code: str):
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
            full_code=data['full_code']
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
        """Get location by ID"""
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
    def get_by_code(cls, full_code: str) -> Optional['Location']:
        """Get location by code"""
        try:
            result = execute_query(
                """
                SELECT id, warehouse_id, full_code
                FROM locations WHERE full_code = %s
                """,
                (full_code,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting location by code {full_code}: {e}")
            return None
    
    @classmethod
    def get_by_warehouse(cls, warehouse_id: str) -> List['Location']:
        """Get all locations in a warehouse"""
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
            logger.error(f"Error getting locations by warehouse {warehouse_id}: {e}")
            return []
    
    @classmethod
    def create(cls, warehouse_id: str, full_code: str) -> Optional['Location']:
        """Create a new location"""
        try:
            result = execute_query(
                """
                INSERT INTO locations (warehouse_id, full_code)
                VALUES (%s, %s)
                RETURNING id, warehouse_id, full_code
                """,
                (warehouse_id, full_code),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating location {full_code}: {e}")
            return None
    
    def update(self, **kwargs) -> bool:
        """Update location attributes"""
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
        """Delete the location"""
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
    
    def get_bins(self) -> List['Bin']:
        """Get all bins in this location"""
        return Bin.get_by_location(self.id)
    
    @property
    def bin_count(self) -> int:
        """Get the number of bins in this location"""
        return len(self.get_bins())
    
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
    """Bin model for warehouse storage locations"""
    
    def __init__(self, id: str, code: str, location_id: str = None,
                 created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        self.code = code
        self.location_id = location_id
        self.created_at = created_at
        self.updated_at = updated_at
    
    def __repr__(self):
        return f"<Bin {self.code} (ID: {self.id})>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bin':
        """Create Bin instance from dictionary"""
        return cls(
            id=str(data['id']),
            code=data['code'],
            location_id=data.get('location_id'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert bin to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'location_id': self.location_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def get_by_id(cls, bin_id: str) -> Optional['Bin']:
        """Get bin by ID"""
        try:
            result = execute_query(
                """
                SELECT id, code, location_id, created_at, updated_at
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
    def get_by_code(cls, code: str) -> Optional['Bin']:
        """Get bin by code"""
        try:
            result = execute_query(
                """
                SELECT id, code, location_id, created_at, updated_at
                FROM bins WHERE code = %s
                """,
                (code,),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting bin by code {code}: {e}")
            return None
    
    @classmethod
    def get_all(cls) -> List['Bin']:
        """Get all bins"""
        try:
            results = execute_query(
                """
                SELECT id, code, location_id, created_at, updated_at
                FROM bins
                ORDER BY code
                """,
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting all bins: {e}")
            return []
    
    @classmethod
    def get_by_warehouse(cls, warehouse_id: str) -> List['Bin']:
        """Get all bins in a warehouse"""
        try:
            results = execute_query(
                """
                SELECT b.id, b.code, b.location_id, b.created_at, b.updated_at
                FROM bins b
                JOIN locations l ON b.location_id = l.id
                WHERE l.warehouse_id = %s
                ORDER BY b.code
                """,
                (warehouse_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting bins by warehouse {warehouse_id}: {e}")
            return []
    
    @classmethod
    def get_by_location(cls, location_id: str) -> List['Bin']:
        """Get all bins in a location"""
        try:
            results = execute_query(
                """
                SELECT id, code, location_id, created_at, updated_at
                FROM bins 
                WHERE location_id = %s
                ORDER BY code
                """,
                (location_id,),
                fetch_all=True
            )
            
            return [cls.from_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting bins by location {location_id}: {e}")
            return []
    
    @classmethod
    def create(cls, code: str, location_id: str = None) -> Optional['Bin']:
        """Create a new bin"""
        try:
            result = execute_query(
                """
                INSERT INTO bins (code, location_id)
                VALUES (%s, %s)
                RETURNING id, code, location_id, created_at, updated_at
                """,
                (code, location_id),
                fetch_one=True
            )
            
            if result:
                return cls.from_dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error creating bin {code}: {e}")
            return None
    
    def update(self, **kwargs) -> bool:
        """Update bin attributes"""
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
        """Delete the bin"""
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
    
    def get_stock_items(self) -> List['StockItem']:
        """Get all stock items in this bin"""
        try:
            from models.stock import StockItem
            return StockItem.get_by_bin(self.id)
        except Exception as e:
            logger.error(f"Error getting stock items for bin {self.id}: {e}")
            return []
