"""
Scanner Service for Inventory Management System
Handles barcode scanning and location operations
"""

from typing import List, Dict, Any, Optional
import logging

from backend.services.base_service import BaseService, ServiceError, ValidationError, NotFoundError
from backend.models.product import Product
from backend.models.warehouse import Bin, Location, Warehouse
from backend.models.stock import StockItem

logger = logging.getLogger(__name__)


class ScannerService(BaseService):
    """Service for scanner operations"""
    
    def __init__(self):
        super().__init__()
    
    def get_location_by_code(self, location_code: str) -> Dict[str, Any]:
        """Get location information by code"""
        try:
            self.log_operation("get_location_by_code", {"location_code": location_code})
            
            # Validate required fields
            self.validate_required_fields({"location_code": location_code})
            
            # Sanitize input
            location_code = self.sanitize_input(location_code)
            
            # Get location
            location = Location.get_by_code(location_code)
            if not location:
                raise NotFoundError(f"Location with code '{location_code}' not found")
            
            # Get warehouse info
            warehouse = Warehouse.get_by_id(location.warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse for location '{location_code}' not found")
            
            # Get bins in this location
            bins = location.get_bins()
            
            # Get stock information for each bin
            bins_data = []
            for bin_obj in bins:
                stock_items = StockItem.get_by_bin(bin_obj.id)
                bin_data = bin_obj.to_dict()
                bin_data['stock_items'] = []
                
                for item in stock_items:
                    product = Product.get_by_id(item.product_id)
                    if product:
                        bin_data['stock_items'].append({
                            'stock_item_id': item.id,
                            'product': product.to_dict(),
                            'quantity': item.on_hand,
                            'reserved': item.qty_reserved,
                            'available': item.available_stock,
                            'batch_id': item.batch_id,
                            'expiry_date': item.expiry_date.isoformat() if item.expiry_date else None
                        })
                
                bins_data.append(bin_data)
            
            return {
                'success': True,
                'location': {
                    'id': location.id,
                    'code': location.code,
                    'name': location.name,
                    'description': location.description,
                    'warehouse': warehouse.to_dict() if warehouse else None,
                    'bins': bins_data
                }
            }
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.log_error("get_location_by_code", e)
            raise ServiceError(f"Failed to get location information: {str(e)}")
    
    def get_product_by_barcode(self, barcode: str) -> Dict[str, Any]:
        """Get product information by barcode"""
        try:
            self.log_operation("get_product_by_barcode", {"barcode": barcode})
            
            # Validate required fields
            self.validate_required_fields({"barcode": barcode})
            
            # Sanitize input
            barcode = self.sanitize_input(barcode)
            
            # Get product by barcode
            product = Product.get_by_barcode(barcode)
            if not product:
                raise NotFoundError(f"Product with barcode '{barcode}' not found")
            
            # Get stock information for this product
            stock_items = StockItem.get_by_product(product.id)
            
            stock_summary = {
                'total_on_hand': sum(item.on_hand for item in stock_items),
                'total_reserved': sum(item.qty_reserved for item in stock_items),
                'total_available': sum(item.available_stock for item in stock_items),
                'locations': []
            }
            
            # Group stock by location
            location_stock = {}
            for item in stock_items:
                bin_obj = Bin.get_by_id(item.bin_id)
                if bin_obj:
                    location = Location.get_by_id(bin_obj.location_id)
                    warehouse = Warehouse.get_by_id(location.warehouse_id) if location else None
                    
                    location_key = f"{warehouse.name}-{location.full_code}" if warehouse and location else "Unknown"
                    
                    if location_key not in location_stock:
                        location_stock[location_key] = {
                            'warehouse': warehouse.to_dict() if warehouse else None,
                            'location': location.to_dict() if location else None,
                            'bin': bin_obj.to_dict(),
                            'quantity': 0,
                            'reserved': 0,
                            'available': 0
                        }
                    
                    location_stock[location_key]['quantity'] += item.on_hand
                    location_stock[location_key]['reserved'] += item.qty_reserved
                    location_stock[location_key]['available'] += item.available_stock
            
            stock_summary['locations'] = list(location_stock.values())
            
            return {
                'success': True,
                'product': product.to_dict(),
                'stock_summary': stock_summary
            }
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.log_error("get_product_by_barcode", e)
            raise ServiceError(f"Failed to get product information: {str(e)}")
    
    def scan_bin(self, bin_code: str) -> Dict[str, Any]:
        """Scan a bin and get its contents"""
        try:
            self.log_operation("scan_bin", {"bin_code": bin_code})
            
            # Validate required fields
            self.validate_required_fields({"bin_code": bin_code})
            
            # Sanitize input
            bin_code = self.sanitize_input(bin_code)
            
            # Get bin by code
            bin_obj = Bin.get_by_code(bin_code)
            if not bin_obj:
                raise NotFoundError(f"Bin with code '{bin_code}' not found")
            
            # Get location and warehouse info
            location = Location.get_by_id(bin_obj.location_id)
            warehouse = Warehouse.get_by_id(location.warehouse_id) if location else None
            
            # Get stock items in this bin
            stock_items = StockItem.get_by_bin(bin_obj.id)
            
            stock_data = []
            for item in stock_items:
                product = Product.get_by_id(item.product_id)
                if product:
                    stock_data.append({
                        'stock_item_id': item.id,
                        'product': product.to_dict(),
                        'quantity': item.on_hand,
                        'reserved': item.qty_reserved,
                        'available': item.available_stock,
                        'batch_id': item.batch_id,
                        'expiry_date': item.expiry_date.isoformat() if item.expiry_date else None
                    })
            
            return {
                'success': True,
                'bin': bin_obj.to_dict(),
                'location': location.to_dict() if location else None,
                'warehouse': warehouse.to_dict() if warehouse else None,
                'stock_items': stock_data,
                'total_items': len(stock_data),
                'total_quantity': sum(item['quantity'] for item in stock_data)
            }
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.log_error("scan_bin", e)
            raise ServiceError(f"Failed to scan bin: {str(e)}")
    
    def search_locations(self, search_term: str) -> List[Dict[str, Any]]:
        """Search locations by code or name"""
        try:
            self.log_operation("search_locations", {"search_term": search_term})
            
            # Sanitize search term
            search_term = self.sanitize_input(search_term)
            
            if not search_term:
                return []
            
            # Search locations
            locations = Location.search(search_term)
            
            results = []
            for location in locations:
                warehouse = Warehouse.get_by_id(location.warehouse_id)
                bin_count = len(location.get_bins())
                
                results.append({
                    'id': location.id,
                    'code': location.code,
                    'name': location.name,
                    'description': location.description,
                    'warehouse': warehouse.to_dict() if warehouse else None,
                    'bin_count': bin_count
                })
            
            return results
            
        except Exception as e:
            self.log_error("search_locations", e)
            raise ServiceError(f"Failed to search locations: {str(e)}")
    
    def search_products(self, search_term: str) -> List[Dict[str, Any]]:
        """Search products by name, SKU, or barcode"""
        try:
            self.log_operation("search_products", {"search_term": search_term})
            
            # Sanitize search term
            search_term = self.sanitize_input(search_term)
            
            if not search_term:
                return []
            
            # Search products
            products = Product.search(search_term)
            
            results = []
            for product in products:
                # Get basic stock info
                stock_items = StockItem.get_by_product(product.id)
                total_quantity = sum(item.on_hand for item in stock_items)
                
                results.append({
                    'id': product.id,
                    'sku': product.sku,
                    'name': product.name,
                    'barcode': product.barcode,
                    'total_quantity': total_quantity,
                    'has_stock': total_quantity > 0
                })
            
            return results
            
        except Exception as e:
            self.log_error("search_products", e)
            raise ServiceError(f"Failed to search products: {str(e)}")
    
    def get_scanner_statistics(self) -> Dict[str, Any]:
        """Get scanner usage statistics"""
        try:
            self.log_operation("get_scanner_statistics", {})
            
            # Get total counts
            total_products = len(Product.get_all())
            total_locations = len(Location.get_all())
            total_bins = len(Bin.get_all())
            total_stock_items = len(StockItem.get_all())
            
            # Get products with barcodes
            products_with_barcodes = [p for p in Product.get_all() if p.barcode]
            barcode_coverage = (len(products_with_barcodes) / total_products * 100) if total_products > 0 else 0
            
            # Get empty bins
            empty_bins = [b for b in Bin.get_all() if not b.has_stock()]
            empty_bin_percentage = (len(empty_bins) / total_bins * 100) if total_bins > 0 else 0
            
            return {
                'total_products': total_products,
                'total_locations': total_locations,
                'total_bins': total_bins,
                'total_stock_items': total_stock_items,
                'products_with_barcodes': len(products_with_barcodes),
                'barcode_coverage_percentage': round(barcode_coverage, 2),
                'empty_bins': len(empty_bins),
                'empty_bin_percentage': round(empty_bin_percentage, 2)
            }
            
        except Exception as e:
            self.log_error("get_scanner_statistics", e)
            raise ServiceError(f"Failed to get scanner statistics: {str(e)}")
    
    def validate_barcode_format(self, barcode: str) -> Dict[str, Any]:
        """Validate barcode format"""
        try:
            self.log_operation("validate_barcode_format", {"barcode": barcode})
            
            # Validate required fields
            self.validate_required_fields({"barcode": barcode})
            
            # Sanitize input
            barcode = self.sanitize_input(barcode)
            
            # Basic barcode validation
            if not barcode:
                return {'valid': False, 'error': 'Barcode cannot be empty'}
            
            if len(barcode) < 8:
                return {'valid': False, 'error': 'Barcode too short (minimum 8 characters)'}
            
            if len(barcode) > 50:
                return {'valid': False, 'error': 'Barcode too long (maximum 50 characters)'}
            
            # Check for valid characters (alphanumeric and common symbols)
            import re
            if not re.match(r'^[A-Za-z0-9\-_\.]+$', barcode):
                return {'valid': False, 'error': 'Barcode contains invalid characters'}
            
            return {'valid': True, 'barcode': barcode}
            
        except (ValidationError):
            raise
        except Exception as e:
            self.log_error("validate_barcode_format", e)
            raise ServiceError(f"Failed to validate barcode format: {str(e)}")
    
    def get_quick_scan_summary(self, scan_data: str) -> Dict[str, Any]:
        """Get quick summary for scanned data (auto-detect type)"""
        try:
            self.log_operation("get_quick_scan_summary", {"scan_data": scan_data})
            
            # Validate required fields
            self.validate_required_fields({"scan_data": scan_data})
            
            # Sanitize input
            scan_data = self.sanitize_input(scan_data)
            
            # Try to identify what was scanned
            result = {
                'scan_data': scan_data,
                'type': 'unknown',
                'data': None,
                'error': None
            }
            
            # Try as location code
            try:
                location = Location.get_by_code(scan_data)
                if location:
                    result['type'] = 'location'
                    result['data'] = self.get_location_by_code(scan_data)
                    return result
            except:
                pass
            
            # Try as bin code
            try:
                bin_obj = Bin.get_by_code(scan_data)
                if bin_obj:
                    result['type'] = 'bin'
                    result['data'] = self.scan_bin(scan_data)
                    return result
            except:
                pass
            
            # Try as product barcode
            try:
                product = Product.get_by_barcode(scan_data)
                if product:
                    result['type'] = 'product'
                    result['data'] = self.get_product_by_barcode(scan_data)
                    return result
            except:
                pass
            
            # Try as product SKU
            try:
                product = Product.get_by_sku(scan_data)
                if product:
                    result['type'] = 'product'
                    result['data'] = self.get_product_by_barcode(product.barcode) if product.barcode else None
                    return result
            except:
                pass
            
            result['error'] = 'Could not identify scanned data as location, bin, or product'
            return result
            
        except (ValidationError):
            raise
        except Exception as e:
            self.log_error("get_quick_scan_summary", e)
            raise ServiceError(f"Failed to get quick scan summary: {str(e)}")
