"""
Warehouse model for Inventory Management System
Pure data container with basic CRUD operations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import re
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
            # Auto-generate next alphabetical code if not provided
            if not code:
                existing = execute_query(
                    "SELECT code FROM warehouses WHERE code IS NOT NULL",
                    fetch_all=True
                ) or []
                used = {str(row.get('code') or '').strip().upper() for row in existing}
                # Find next single letter A..Z not used
                code_candidate = None
                for i in range(ord('A'), ord('Z') + 1):
                    letter = chr(i)
                    if letter not in used:
                        code_candidate = letter
                        break
                code = code_candidate or None

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

    def get_hierarchical_locations(self) -> Dict[str, Any]:
        """Build hierarchical structure (areas → racks → levels → bins) for this warehouse.

        Heuristics:
        - Parse Location.full_code to derive (area, rack, level) codes using separators ("-", ":", " ").
        - Prefer tokens starting with A/R/L; otherwise fall back to first/second/third tokens.
        - If parsing fails, fall back to defaults (A, R1, L1) for that location only.
        - Aggregate counts for total/occupied bins at each level.
        """
        try:
            # Local imports to avoid circular dependencies
            from backend.models.warehouse import Location, Bin
            from backend.models.stock import StockItem

            # Load all locations for this warehouse
            locations = Location.get_by_warehouse(self.id)

            # Prepare containers
            total_locations = len(locations)
            total_bins = 0
            occupied_bins = 0

            areas: Dict[str, Any] = {}

            def parse_location(full_code: str) -> Dict[str, str]:
                """Derive area, rack, level codes from a location full_code using heuristics."""
                default = {'area': 'A01', 'rack': 'RA', 'level': 'L01', 'area_name': 'Area 1', 'rack_name': 'Rack A', 'level_name': 'Level 1'}
                if not full_code:
                    return default
                code = str(full_code).strip()
                # Specific pattern: WarehouseLetter AreaNumber RackLetter LevelNumber e.g., C1B3
                m = re.match(r"^([A-Z])([0-9]+)([A-Z])([0-9]+)$", code.upper())
                if m:
                    area_num = int(m.group(2))
                    rack_letter = m.group(3)
                    level_num = int(m.group(4))
                    return {
                        'area': f"A{area_num:02d}",
                        'rack': f"R{rack_letter}",
                        'level': f"L{level_num:02d}",
                        'area_name': f"Area {area_num}",
                        'rack_name': f"Rack {rack_letter}",
                        'level_name': f"Level {level_num}"
                    }
                # Split by non-alphanumeric separators
                tokens = [t for t in re.split(r"[^A-Za-z0-9]+", code.upper()) if t]
                if not tokens:
                    return default

                area = None
                rack = None
                level = None

                # Try to find explicit A/R/L prefixed tokens
                for t in tokens:
                    if not area and t.startswith('A') and len(t) > 1:
                        area = t
                    if not rack and t.startswith('R') and len(t) > 1:
                        rack = t
                    if not level and t.startswith('L') and len(t) > 1:
                        level = t

                # Fallbacks by position
                if not area:
                    area = tokens[0] if tokens else 'A1'
                    if not area.startswith('A'):
                        area = f"A{area}"
                if not rack:
                    cand = tokens[1] if len(tokens) > 1 else 'A'
                    rack = cand if cand.startswith('R') else f"R{cand}"
                if not level:
                    cand = tokens[2] if len(tokens) > 2 else '1'
                    level = cand if cand.startswith('L') else f"L{cand}"

                # Extract numeric/letter parts for friendly names and pad
                area_num = int(re.sub(r"[^0-9]", "", area) or 1)
                level_num = int(re.sub(r"[^0-9]", "", level) or 1)
                rack_letter = re.sub(r"[^A-Z]", "", rack) or 'A'

                return {
                    'area': f"A{area_num:02d}",
                    'rack': f"R{rack_letter}",
                    'level': f"L{level_num:02d}",
                    'area_name': f"Area {area_num}",
                    'rack_name': f"Rack {rack_letter}",
                    'level_name': f"Level {level_num}"
                }

            # Populate bins per location
            for loc in locations:
                parts = parse_location(loc.full_code)
                area_code = parts['area']
                rack_code = parts['rack']
                level_code = parts['level']

                if area_code not in areas:
                    areas[area_code] = {
                        'name': parts.get('area_name', area_code),
                        'total_locations': 0,
                        'total_bins': 0,
                        'occupied_bins': 0,
                        'racks': {}
                    }
                area_ref = areas[area_code]
                area_ref['total_locations'] += 1

                if rack_code not in area_ref['racks']:
                    area_ref['racks'][rack_code] = {
                        'name': parts.get('rack_name', rack_code),
                        'total_locations': 0,
                        'total_bins': 0,
                        'occupied_bins': 0,
                        'levels': {}
                    }
                rack_ref = area_ref['racks'][rack_code]
                rack_ref['total_locations'] += 1

                if level_code not in rack_ref['levels']:
                    rack_ref['levels'][level_code] = {
                        'name': parts.get('level_name', level_code),
                        'total_bins': 0,
                        'occupied_bins': 0,
                        'bins': [],
                        'location_code': loc.full_code or ''
                    }
                level_ref = rack_ref['levels'][level_code]
                # Ensure location_code is set even if no bins exist
                if not level_ref.get('location_code'):
                    level_ref['location_code'] = loc.full_code or ''

                # Fetch bins for this location
                bins = Bin.get_by_location(loc.id)
                for b in bins:
                    # Fetch stock items to determine occupancy and counts
                    stock_items = StockItem.get_by_bin(b.id)
                    stock_count = len(stock_items)
                    total_qty = 0
                    for si in stock_items:
                        try:
                            on_hand = getattr(si, 'on_hand', 0) or 0
                        except Exception:
                            on_hand = 0
                        total_qty += on_hand

                    is_occupied = stock_count > 0

                    bin_entry = {
                        'code': b.code,
                        'full_code': loc.full_code or b.code,
                        'occupied': is_occupied,
                        'stock_count': stock_count,
                        'total_stock_quantity': total_qty,
                        'is_empty_location': False
                    }

                    level_ref['bins'].append(bin_entry)
                    level_ref['total_bins'] += 1
                    if is_occupied:
                        level_ref['occupied_bins'] += 1

                    # Update aggregates
                    total_bins += 1
                    if is_occupied:
                        occupied_bins += 1
                    rack_ref['total_bins'] += 1
                    if is_occupied:
                        rack_ref['occupied_bins'] += 1
                    area_ref['total_bins'] += 1
                    if is_occupied:
                        area_ref['occupied_bins'] += 1

            hierarchical_data = {
                'total_locations': total_locations,
                'total_bins': total_bins,
                'occupied_bins': occupied_bins,
                'areas': areas
            }

            return hierarchical_data

        except Exception as e:
            logger.error(f"Error building hierarchical locations for warehouse {self.id}: {e}")
            # Return a safe empty structure so the template can render an empty state
            return {
                'total_locations': 0,
                'total_bins': 0,
                'occupied_bins': 0,
                'areas': {}
            }


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