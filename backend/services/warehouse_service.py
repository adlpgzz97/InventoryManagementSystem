"""
Warehouse Service for Inventory Management System
Handles warehouse, location, and bin business logic
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from backend.services.base_service import BaseService, ServiceError, ValidationError, NotFoundError
from backend.models.warehouse import Warehouse, Location, Bin
from backend.models.stock import StockItem
from backend.repositories.warehouse_repository import WarehouseRepository
from backend.utils.database import execute_query

logger = logging.getLogger(__name__)


class WarehouseService(BaseService):
    """Service for warehouse management operations"""
    
    def __init__(self):
        super().__init__()
        self.warehouse_repository = WarehouseRepository()
    
    def get_all_warehouses(self, search_term: str = '', filter_type: str = '') -> List[Dict[str, Any]]:
        """Get all warehouses with optional filtering"""
        try:
            self.log_operation("get_all_warehouses", {"search_term": search_term, "filter_type": filter_type})
            
            if filter_type == 'empty':
                warehouses = Warehouse.get_all()
                warehouses = [w for w in warehouses if not w.get_bins()]
            elif filter_type == 'full':
                warehouses = Warehouse.get_all()
                warehouses = [w for w in warehouses if w.get_utilization_percentage() > 80]
            else:
                warehouses = Warehouse.search(search_term) if search_term else Warehouse.get_all()
            
            return [warehouse.to_dict() for warehouse in warehouses]
            
        except Exception as e:
            self.log_error("get_all_warehouses", e)
            raise ServiceError(f"Failed to retrieve warehouses: {str(e)}")
    
    def get_warehouse_by_id(self, warehouse_id: str) -> Dict[str, Any]:
        """Get warehouse by ID"""
        try:
            self.log_operation("get_warehouse_by_id", {"warehouse_id": warehouse_id})
            
            warehouse = Warehouse.get_by_id(warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse with ID {warehouse_id} not found")
            
            return warehouse.to_dict()
            
        except NotFoundError:
            raise
        except Exception as e:
            self.log_error("get_warehouse_by_id", e)
            raise ServiceError(f"Failed to retrieve warehouse: {str(e)}")
    
    def create_warehouse(self, name: str, address: str = '', code: str = '') -> Dict[str, Any]:
        """Create a new warehouse"""
        try:
            self.log_operation("create_warehouse", {"name": name, "address": address, "code": code})
            
            # Validate required fields
            self.validate_required_fields({"name": name})
            
            # Sanitize inputs
            name = self.sanitize_input(name)
            address = self.sanitize_input(address)
            code = self.sanitize_input(code)
            
            # Check if warehouse with same name already exists
            existing_warehouses = Warehouse.search(name)
            if existing_warehouses and any(w.name.lower() == name.lower() for w in existing_warehouses):
                raise ValidationError(f"Warehouse with name '{name}' already exists")
            
            # Create warehouse
            warehouse = Warehouse.create(
                name=name,
                address=address,
                code=code
            )
            
            if not warehouse:
                raise ServiceError("Failed to create warehouse")
            
            return warehouse.to_dict()
            
        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            self.log_error("create_warehouse", e)
            raise ServiceError(f"Failed to create warehouse: {str(e)}")
    
    def update_warehouse(self, warehouse_id: str, name: str, address: str = '', code: str = '') -> Dict[str, Any]:
        """Update an existing warehouse"""
        try:
            self.log_operation("update_warehouse", {"warehouse_id": warehouse_id, "name": name, "address": address, "code": code})
            
            # Validate required fields
            self.validate_required_fields({"warehouse_id": warehouse_id, "name": name})
            
            # Sanitize inputs
            name = self.sanitize_input(name)
            address = self.sanitize_input(address)
            code = self.sanitize_input(code)
            
            # Get existing warehouse
            warehouse = Warehouse.get_by_id(warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse with ID {warehouse_id} not found")
            
            # Check if name change conflicts with existing warehouse
            if name != warehouse.name:
                existing_warehouses = Warehouse.search(name)
                if existing_warehouses and any(w.name.lower() == name.lower() and w.id != warehouse_id for w in existing_warehouses):
                    raise ValidationError(f"Warehouse with name '{name}' already exists")
            
            # Update warehouse
            updated_warehouse = warehouse.update(
                name=name,
                address=address,
                code=code
            )
            
            if not updated_warehouse:
                raise ServiceError("Failed to update warehouse")
            
            return updated_warehouse.to_dict()
            
        except (ValidationError, NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.log_error("update_warehouse", e)
            raise ServiceError(f"Failed to update warehouse: {str(e)}")
    
    def delete_warehouse(self, warehouse_id: str) -> bool:
        """Delete a warehouse"""
        try:
            self.log_operation("delete_warehouse", {"warehouse_id": warehouse_id})
            
            # Validate required fields
            self.validate_required_fields({"warehouse_id": warehouse_id})
            
            # Get warehouse
            warehouse = Warehouse.get_by_id(warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse with ID {warehouse_id} not found")
            
            # Check if warehouse has stock
            if warehouse.has_stock():
                raise ValidationError("Cannot delete warehouse with existing stock")
            
            # Delete warehouse
            success = warehouse.delete()
            if not success:
                raise ServiceError("Failed to delete warehouse")
            
            return True
            
        except (ValidationError, NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.log_error("delete_warehouse", e)
            raise ServiceError(f"Failed to delete warehouse: {str(e)}")
    
    def get_warehouse_utilization(self, warehouse_id: str) -> Dict[str, Any]:
        """Get warehouse utilization statistics"""
        try:
            self.log_operation("get_warehouse_utilization", {"warehouse_id": warehouse_id})
            
            # Validate required fields
            self.validate_required_fields({"warehouse_id": warehouse_id})
            
            # Get warehouse
            warehouse = Warehouse.get_by_id(warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse with ID {warehouse_id} not found")
            
            # Get utilization data
            total_bins = len(warehouse.get_bins())
            occupied_bins = len([b for b in warehouse.get_bins() if b.has_stock()])
            utilization_percentage = warehouse.get_utilization_percentage()
            
            # Get stock summary
            stock_summary = warehouse.get_stock_summary()
            
            return {
                "warehouse_id": warehouse_id,
                "total_bins": total_bins,
                "occupied_bins": occupied_bins,
                "utilization_percentage": utilization_percentage,
                "stock_summary": stock_summary
            }
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.log_error("get_warehouse_utilization", e)
            raise ServiceError(f"Failed to get warehouse utilization: {str(e)}")
    
    def get_locations_by_warehouse(self, warehouse_id: str) -> List[Dict[str, Any]]:
        """Get all locations within a warehouse"""
        try:
            self.log_operation("get_locations_by_warehouse", {"warehouse_id": warehouse_id})
            
            # Validate required fields
            self.validate_required_fields({"warehouse_id": warehouse_id})
            
            # Get warehouse
            warehouse = Warehouse.get_by_id(warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse with ID {warehouse_id} not found")
            
            # Get locations
            from backend.models.warehouse import Location
            locations = Location.get_by_warehouse(warehouse_id)
            return [location.to_dict() for location in locations]
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.log_error("get_locations_by_warehouse", e)
            raise ServiceError(f"Failed to get locations: {str(e)}")
    
    def create_location(self, warehouse_id: str, code: str, name: str, description: str = '') -> Dict[str, Any]:
        """Create a new location within a warehouse"""
        try:
            self.log_operation("create_location", {"warehouse_id": warehouse_id, "code": code, "name": name, "description": description})
            
            # Validate required fields
            self.validate_required_fields({"warehouse_id": warehouse_id, "code": code, "name": name})
            
            # Sanitize inputs
            code = self.sanitize_input(code)
            name = self.sanitize_input(name)
            description = self.sanitize_input(description)
            
            # Get warehouse
            warehouse = Warehouse.get_by_id(warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse with ID {warehouse_id} not found")
            
            # Check if location code already exists in this warehouse
            from backend.models.warehouse import Location
            existing_locations = Location.get_by_warehouse(warehouse_id)
            if any(l.code == code for l in existing_locations):
                raise ValidationError(f"Location with code '{code}' already exists in this warehouse")
            
            # Create location
            location = Location.create(
                warehouse_id=warehouse_id,
                code=code,
                name=name,
                description=description
            )
            
            if not location:
                raise ServiceError("Failed to create location")
            
            return location.to_dict()
            
        except (ValidationError, NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.log_error("create_location", e)
            raise ServiceError(f"Failed to create location: {str(e)}")
    
    def get_bins_by_location(self, location_id: str) -> List[Dict[str, Any]]:
        """Get all bins within a location"""
        try:
            self.log_operation("get_bins_by_location", {"location_id": location_id})
            
            # Validate required fields
            self.validate_required_fields({"location_id": location_id})
            
            # Get location
            location = Location.get_by_id(location_id)
            if not location:
                raise NotFoundError(f"Location with ID {location_id} not found")
            
            # Get bins
            bins = location.get_bins()
            return [bin_obj.to_dict() for bin_obj in bins]
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.log_error("get_bins_by_location", e)
            raise ServiceError(f"Failed to get bins: {str(e)}")
    
    def create_bin(self, location_id: str, code: str, name: str, description: str = '') -> Dict[str, Any]:
        """Create a new bin within a location"""
        try:
            self.log_operation("create_bin", {"location_id": location_id, "code": code, "name": name, "description": description})
            
            # Validate required fields
            self.validate_required_fields({"location_id": location_id, "code": code, "name": name})
            
            # Sanitize inputs
            code = self.sanitize_input(code)
            name = self.sanitize_input(name)
            description = self.sanitize_input(description)
            
            # Get location
            location = Location.get_by_id(location_id)
            if not location:
                raise NotFoundError(f"Location with ID {location_id} not found")
            
            # Check if bin code already exists in this location
            existing_bins = location.get_bins()
            if any(b.code == code for b in existing_bins):
                raise ValidationError(f"Bin with code '{code}' already exists in this location")
            
            # Create bin
            bin_obj = Bin.create(
                location_id=location_id,
                code=code,
                name=name,
                description=description
            )
            
            if not bin_obj:
                raise ServiceError("Failed to create bin")
            
            return bin_obj.to_dict()
            
        except (ValidationError, NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.log_error("create_bin", e)
            raise ServiceError(f"Failed to create bin: {str(e)}")
    
    def get_bin_stock(self, bin_id: str) -> List[Dict[str, Any]]:
        """Get stock items in a specific bin"""
        try:
            self.log_operation("get_bin_stock", {"bin_id": bin_id})
            
            # Validate required fields
            self.validate_required_fields({"bin_id": bin_id})
            
            # Get bin
            bin_obj = Bin.get_by_id(bin_id)
            if not bin_obj:
                raise NotFoundError(f"Bin with ID {bin_id} not found")
            
            # Get stock items
            stock_items = StockItem.get_by_bin(bin_id)
            return [item.to_dict() for item in stock_items]
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.log_error("get_bin_stock", e)
            raise ServiceError(f"Failed to get bin stock: {str(e)}")
    
    def search_warehouses(self, search_term: str) -> List[Dict[str, Any]]:
        """Search warehouses by name or code"""
        try:
            self.log_operation("search_warehouses", {"search_term": search_term})
            
            # Sanitize search term
            search_term = self.sanitize_input(search_term)
            
            if not search_term:
                return []
            
            # Search warehouses
            warehouses = Warehouse.search(search_term)
            return [warehouse.to_dict() for warehouse in warehouses]
            
        except Exception as e:
            self.log_error("search_warehouses", e)
            raise ServiceError(f"Failed to search warehouses: {str(e)}")
    
    def get_warehouse_statistics(self) -> Dict[str, Any]:
        """Get overall warehouse statistics"""
        try:
            self.log_operation("get_warehouse_statistics", {})
            
            # Get all warehouses
            warehouses = Warehouse.get_all()
            
            from backend.models.warehouse import Location, Bin
            from backend.models.stock import StockItem
            
            total_warehouses = len(warehouses)
            total_locations = 0
            total_bins = 0
            total_stock_items = 0
            
            for warehouse in warehouses:
                locations = Location.get_by_warehouse(warehouse.id)
                total_locations += len(locations)
                
                for location in locations:
                    bins = Bin.get_by_location(location.id)
                    total_bins += len(bins)
                    
                    for bin_obj in bins:
                        stock_items = StockItem.get_by_bin(bin_obj.id)
                        total_stock_items += len(stock_items)
            
            # Calculate utilization
            utilization_data = []
            for warehouse in warehouses:
                utilization_data.append({
                    "warehouse_id": warehouse.id,
                    "name": warehouse.name,
                    "utilization_percentage": warehouse.get_utilization_percentage(),
                    "total_bins": len(warehouse.get_bins()),
                    "occupied_bins": len([b for b in warehouse.get_bins() if b.has_stock()])
                })
            
            return {
                "total_warehouses": total_warehouses,
                "total_locations": total_locations,
                "total_bins": total_bins,
                "total_stock_items": total_stock_items,
                "utilization_data": utilization_data
            }
            
        except Exception as e:
            self.log_error("get_warehouse_statistics", e)
            raise ServiceError(f"Failed to get warehouse statistics: {str(e)}")
    
    def get_warehouse_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get warehouse by code"""
        try:
            self.log_operation("get_warehouse_by_code", {"code": code})
            
            warehouse = self.warehouse_repository.get_by_code(code)
            if warehouse:
                return warehouse.to_dict()
            return None
            
        except Exception as e:
            self.log_error("get_warehouse_by_code", e)
            return None
    
    def get_warehouse_hierarchy(self, warehouse_id: str) -> Optional[Dict[str, Any]]:
        """Get warehouse hierarchy"""
        try:
            self.log_operation("get_warehouse_hierarchy", {"warehouse_id": warehouse_id})
            
            hierarchy = self.warehouse_repository.get_warehouse_hierarchy(warehouse_id)
            return hierarchy
            
        except Exception as e:
            self.log_error("get_warehouse_hierarchy", e)
            return None
