"""
Product Service for Inventory Management System
Handles all business logic for product operations
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_service import BaseService, ServiceError, ValidationError, NotFoundError
from backend.models.product import Product
from backend.repositories.product_repository import ProductRepository


class ProductService(BaseService):
    """Service for product business logic"""
    
    def __init__(self):
        super().__init__()
        self.product_repository = ProductRepository()
    
    def get_service_name(self) -> str:
        return "ProductService"

    def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """Aggregate product details for the details modal/API."""
        try:
            self.log_operation("get_product_details", {"product_id": product_id})
            if not product_id:
                return {"error": "Product ID is required"}

            # Sanitize incoming ID (strip quotes/braces/whitespace)
            pid = str(product_id).strip().strip('"\'{}')

            # Try by UUID first
            product = self.product_repository.get_by_id(pid)
            if not product:
                # Fallbacks: try by SKU or barcode if UUID lookup failed
                try:
                    product = self.product_repository.get_by_sku(pid)
                except Exception:
                    product = None
                if not product:
                    try:
                        product = self.product_repository.get_by_barcode(pid)
                    except Exception:
                        product = None
                if not product:
                    return {"error": "Product not found"}

            # Basic product info
            product_dict: Dict[str, Any] = product.to_dict()
            # Category info if available
            try:
                category = getattr(product, 'category', None)
                if category:
                    product_dict['category'] = {
                        'id': category.id,
                        'code': category.code,
                        'description': category.description
                    }
                else:
                    product_dict['category'] = None
            except Exception:
                product_dict['category'] = None

            # Stock summary: locations and quantities
            from backend.models.stock import StockItem
            from backend.utils.database import execute_query

            # Aggregate stock by location
            stock_rows = execute_query(
                """
                SELECT b.id AS bin_id,
                       b.code AS bin_code,
                       l.full_code AS location_code,
                       w.name AS warehouse_name,
                       COALESCE(si.on_hand,0) AS on_hand,
                       COALESCE(si.qty_reserved,0) AS qty_reserved
                FROM bins b
                JOIN locations l ON b.location_id = l.id
                JOIN warehouses w ON l.warehouse_id = w.id
                LEFT JOIN stock_items si ON si.bin_id = b.id AND si.product_id = %s
                WHERE si.product_id = %s
                ORDER BY w.name, l.full_code, b.code
                """,
                (product_id, product_id),
                fetch_all=True
            ) or []

            total_on_hand = 0
            total_reserved = 0
            locations: Dict[str, Dict[str, Any]] = {}
            for row in stock_rows:
                loc = row.get('location_code') or 'Unknown'
                if loc not in locations:
                    locations[loc] = {
                        'bins': [],
                        'on_hand': 0,
                        'qty_reserved': 0
                    }
                bin_entry = {
                    'bin_id': row.get('bin_id'),
                    'bin_code': row.get('bin_code'),
                    'on_hand': row.get('on_hand', 0),
                    'qty_reserved': row.get('qty_reserved', 0)
                }
                locations[loc]['bins'].append(bin_entry)
                locations[loc]['on_hand'] += bin_entry['on_hand']
                locations[loc]['qty_reserved'] += bin_entry['qty_reserved']
                total_on_hand += bin_entry['on_hand']
                total_reserved += bin_entry['qty_reserved']

            # Flatten locations to an array expected by the frontend helper
            stock_locations: list = []
            for loc_code, loc_data in locations.items():
                for b in loc_data['bins']:
                    letWarehouse = None
                    # Try to pull from original stock_rows for this loc/bin
                    try:
                        letWarehouse = next((r.get('warehouse_name') for r in stock_rows if r.get('bin_id') == b.get('bin_id')), None)
                    except Exception:
                        letWarehouse = None
                    if not letWarehouse and loc_code:
                        # Fallback from first character of location code
                        firstChar = str(loc_code)[0]
                        letWarehouse = f"Warehouse {firstChar}"
                    stock_locations.append({
                        'warehouse_name': letWarehouse,
                        'aisle': (loc_code or ''),
                        'bin': (b.get('bin_code') or ''),
                        'on_hand': b.get('on_hand', 0),
                        'qty_reserved': b.get('qty_reserved', 0),
                        'batch_id': None,
                        'expiry_date': None,
                        'created_at': None
                    })

            # Summary
            summary = {
                'total_locations': len(stock_locations),
                'total_transactions': 0
            }

            # Minimal forecasting model the UI expects
            avg_daily_usage = 1.0
            safety_stock = 0
            lead_time_days = 7
            reorder_point = 10
            days_of_stock = float('inf') if avg_daily_usage == 0 else (total_on_hand / avg_daily_usage)
            stock_status = 'low' if total_on_hand <= reorder_point else 'ok'
            forecasting = {
                'current_stock': total_on_hand,
                'reorder_point': reorder_point,
                'safety_stock': safety_stock,
                'avg_daily_usage': avg_daily_usage,
                'lead_time_days': lead_time_days,
                'days_of_stock': days_of_stock,
                'stock_status': stock_status
            }

            # Warehouse distribution (available by warehouse)
            warehouse_distribution = execute_query(
                """
                SELECT w.name AS warehouse_name,
                       COALESCE(SUM(GREATEST(si.on_hand - si.qty_reserved, 0)), 0) AS total_available
                FROM stock_items si
                JOIN bins b ON si.bin_id = b.id
                JOIN locations l ON b.location_id = l.id
                JOIN warehouses w ON l.warehouse_id = w.id
                WHERE si.product_id = %s
                GROUP BY w.name
                ORDER BY w.name
                """,
                (pid,),
                fetch_all=True
            ) or []

            # Stock movement trends (last 30 days)
            stock_trends = execute_query(
                """
                SELECT DATE(st.created_at) AS date,
                       SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) AS received,
                       SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END) AS shipped
                FROM stock_transactions st
                JOIN stock_items si ON st.stock_item_id = si.id
                WHERE si.product_id = %s
                  AND st.created_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(st.created_at)
                ORDER BY date
                """,
                (pid,),
                fetch_all=True
            ) or []

            # Compute cumulative on_hand series so it reflects running inventory level.
            # Derive starting balance so that final day approximates current total_on_hand.
            net_total = 0
            for row in stock_trends:
                rec = row.get('received') or 0
                shp = row.get('shipped') or 0
                net_total += (rec - shp)
            starting_balance = total_on_hand - net_total
            # If negative (incomplete history), clamp to 0 for display purposes
            if starting_balance is None:
                starting_balance = 0
            starting_balance = max(starting_balance, 0)

            running = starting_balance
            for row in stock_trends:
                rec = row.get('received') or 0
                shp = row.get('shipped') or 0
                running += (rec - shp)
                row['on_hand'] = max(running, 0)

            response_data = {
                'product': product_dict,
                'stock_locations': stock_locations,
                'summary': summary,
                'forecasting': forecasting,
                'transaction_history': [],
                'warehouse_distribution': warehouse_distribution,
                'stock_trends': stock_trends,
                'expiry_alerts': []
            }

            return response_data
        except Exception as e:
            self.log_error("get_product_details", e, {"product_id": product_id})
            return {"error": f"Failed to get product details: {str(e)}"}
    
    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        try:
            self.log_operation("get_product_by_id", {"product_id": product_id})
            
            if not product_id:
                raise ValidationError("Product ID is required")
            
            product = self.product_repository.get_by_id(product_id)
            
            if product:
                self.log_operation("get_product_by_id_success", {"product_id": product_id})
                return product
            else:
                self.log_operation("get_product_by_id_not_found", {"product_id": product_id})
                return None
                
        except Exception as e:
            self.log_error("get_product_by_id", e, {"product_id": product_id})
            if isinstance(e, ValidationError):
                raise
            raise ServiceError(f"Failed to get product by ID: {str(e)}")
    
    def get_product_by_barcode(self, barcode: str) -> Optional[Product]:
        """Get product by barcode"""
        try:
            self.log_operation("get_product_by_barcode", {"barcode": barcode})
            
            if not barcode:
                raise ValidationError("Barcode is required")
            
            product = self.product_repository.get_by_barcode(barcode)
            
            if product:
                self.log_operation("get_product_by_barcode_success", {"barcode": barcode})
                return product
            else:
                self.log_operation("get_product_by_barcode_not_found", {"barcode": barcode})
                return None
                
        except Exception as e:
            self.log_error("get_product_by_barcode", e, {"barcode": barcode})
            if isinstance(e, ValidationError):
                raise
            raise ServiceError(f"Failed to get product by barcode: {str(e)}")
    
    def get_all_products(self) -> List[Product]:
        """Get all products"""
        try:
            self.log_operation("get_all_products")
            
            products = self.product_repository.get_all()
            
            self.log_operation("get_all_products_success", {"count": len(products)})
            return products
                
        except Exception as e:
            self.log_error("get_all_products", e)
            raise ServiceError(f"Failed to get all products: {str(e)}")
    
    def search_products(self, search_term: str, limit: Optional[int] = None) -> List[Product]:
        """Search products by name, description, or SKU"""
        try:
            self.log_operation("search_products", {"search_term": search_term, "limit": limit})
            
            if not search_term:
                return self.get_all_products()
            
            products = self.product_repository.search_products(search_term, limit)
            
            self.log_operation("search_products_success", {"search_term": search_term, "count": len(products)})
            return products
                
        except Exception as e:
            self.log_error("search_products", e, {"search_term": search_term})
            raise ServiceError(f"Failed to search products: {str(e)}")
    
    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product"""
        try:
            self.log_operation("create_product", product_data)
            
            # Validate required fields
            required_fields = ['name', 'sku']
            self.validate_required_fields(product_data, required_fields)
            
            # Validate SKU uniqueness
            if self.product_repository.get_by_sku(product_data['sku']):
                raise ValidationError(f"Product with SKU '{product_data['sku']}' already exists")
            
            # Validate barcode uniqueness if provided
            if product_data.get('barcode') and self.product_repository.get_by_barcode(product_data['barcode']):
                raise ValidationError(f"Product with barcode '{product_data['barcode']}' already exists")
            
            # Sanitize input
            sanitized_data = self.sanitize_input(product_data)
            
            # Create product
            product = self.product_repository.create(sanitized_data)
            
            self.log_operation("create_product_success", {"product_id": product.id})
            
            return self.create_response(
                success=True,
                data=product.to_dict(),
                message="Product created successfully"
            )
                
        except Exception as e:
            self.log_error("create_product", e, product_data)
            if isinstance(e, ValidationError):
                return self.create_response(success=False, error=str(e))
            raise ServiceError(f"Failed to create product: {str(e)}")
    
    def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing product"""
        try:
            self.log_operation("update_product", {"product_id": product_id, "data": product_data})
            
            if not product_id:
                raise ValidationError("Product ID is required")
            
            # Check if product exists
            existing_product = self.product_repository.get_by_id(product_id)
            if not existing_product:
                raise NotFoundError(f"Product with ID '{product_id}' not found")
            
            # Validate SKU uniqueness if changing
            if 'sku' in product_data and product_data['sku'] != existing_product.sku:
                if self.product_repository.get_by_sku(product_data['sku']):
                    raise ValidationError(f"Product with SKU '{product_data['sku']}' already exists")
            
            # Validate barcode uniqueness if changing
            if 'barcode' in product_data and product_data['barcode'] != existing_product.barcode:
                if product_data['barcode'] and self.product_repository.get_by_barcode(product_data['barcode']):
                    raise ValidationError(f"Product with barcode '{product_data['barcode']}' already exists")
            
            # Sanitize input
            sanitized_data = self.sanitize_input(product_data)
            
            # Update product
            updated_product = self.product_repository.update(product_id, sanitized_data)
            
            if updated_product:
                self.log_operation("update_product_success", {"product_id": product_id})
                
                return self.create_response(
                    success=True,
                    data=updated_product.to_dict(),
                    message="Product updated successfully"
                )
            else:
                raise ServiceError("Failed to update product")
                
        except Exception as e:
            self.log_error("update_product", e, {"product_id": product_id, "data": product_data})
            if isinstance(e, (ValidationError, NotFoundError)):
                return self.create_response(success=False, error=str(e))
            raise ServiceError(f"Failed to update product: {str(e)}")
    
    def delete_product(self, product_id: str) -> Dict[str, Any]:
        """Delete a product"""
        try:
            self.log_operation("delete_product", {"product_id": product_id})
            
            if not product_id:
                raise ValidationError("Product ID is required")
            
            # Check if product exists
            existing_product = self.product_repository.get_by_id(product_id)
            if not existing_product:
                raise NotFoundError(f"Product with ID '{product_id}' not found")
            
            # Delete product
            success = self.product_repository.delete(product_id)
            
            if success:
                self.log_operation("delete_product_success", {"product_id": product_id})
                
                return self.create_response(
                    success=True,
                    message="Product deleted successfully"
                )
            else:
                raise ServiceError("Failed to delete product")
                
        except Exception as e:
            self.log_error("delete_product", e, {"product_id": product_id})
            if isinstance(e, (ValidationError, NotFoundError)):
                return self.create_response(success=False, error=str(e))
            raise ServiceError(f"Failed to delete product: {str(e)}")
    
    def get_products_with_stock(self) -> List[Dict[str, Any]]:
        """Get products with their current stock levels"""
        try:
            self.log_operation("get_products_with_stock")
            
            products_with_stock = self.product_repository.get_products_with_stock()
            
            self.log_operation("get_products_with_stock_success", {"count": len(products_with_stock)})
            return products_with_stock
                
        except Exception as e:
            self.log_error("get_products_with_stock", e)
            raise ServiceError(f"Failed to get products with stock: {str(e)}")
    
    def get_low_stock_products(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """Get products with stock below threshold"""
        try:
            self.log_operation("get_low_stock_products", {"threshold": threshold})
            
            low_stock_products = self.product_repository.get_low_stock_products(threshold)
            
            self.log_operation("get_low_stock_products_success", {"count": len(low_stock_products)})
            return low_stock_products
                
        except Exception as e:
            self.log_error("get_low_stock_products", e, {"threshold": threshold})
            raise ServiceError(f"Failed to get low stock products: {str(e)}")
    
    def get_out_of_stock_products(self) -> List[Dict[str, Any]]:
        """Get products with no available stock"""
        try:
            self.log_operation("get_out_of_stock_products")
            
            out_of_stock_products = self.product_repository.get_out_of_stock_products()
            
            self.log_operation("get_out_of_stock_products_success", {"count": len(out_of_stock_products)})
            return out_of_stock_products
                
        except Exception as e:
            self.log_error("get_out_of_stock_products", e)
            raise ServiceError(f"Failed to get out of stock products: {str(e)}")
    
    def get_products_by_warehouse(self, warehouse_id: str) -> List[Dict[str, Any]]:
        """Get products available in a specific warehouse"""
        try:
            self.log_operation("get_products_by_warehouse", {"warehouse_id": warehouse_id})
            
            if not warehouse_id:
                raise ValidationError("Warehouse ID is required")
            
            products = self.product_repository.get_products_by_warehouse(warehouse_id)
            
            self.log_operation("get_products_by_warehouse_success", {"warehouse_id": warehouse_id, "count": len(products)})
            return products
                
        except Exception as e:
            self.log_error("get_products_by_warehouse", e, {"warehouse_id": warehouse_id})
            if isinstance(e, ValidationError):
                raise
            raise ServiceError(f"Failed to get products by warehouse: {str(e)}")
    
    def get_product_statistics(self) -> Dict[str, Any]:
        """Get product statistics for dashboard"""
        try:
            self.log_operation("get_product_statistics")
            
            stats = self.product_repository.get_product_statistics()
            
            self.log_operation("get_product_statistics_success")
            return stats
                
        except Exception as e:
            self.log_error("get_product_statistics", e)
            raise ServiceError(f"Failed to get product statistics: {str(e)}")
    
    def get_products_with_expiring_batches(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get products with batches expiring soon"""
        try:
            self.log_operation("get_products_with_expiring_batches", {"days_ahead": days_ahead})
            
            expiring_products = self.product_repository.get_products_with_expiring_batches(days_ahead)
            
            self.log_operation("get_products_with_expiring_batches_success", {"count": len(expiring_products)})
            return expiring_products
                
        except Exception as e:
            self.log_error("get_products_with_expiring_batches", e, {"days_ahead": days_ahead})
            raise ServiceError(f"Failed to get products with expiring batches: {str(e)}")
    
    def get_product_usage_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get product usage statistics based on transactions"""
        try:
            self.log_operation("get_product_usage_stats", {"days": days})
            
            usage_stats = self.product_repository.get_product_usage_stats(days)
            
            self.log_operation("get_product_usage_stats_success", {"count": len(usage_stats)})
            return usage_stats
                
        except Exception as e:
            self.log_error("get_product_usage_stats", e, {"days": days})
            raise ServiceError(f"Failed to get product usage stats: {str(e)}")
    
    def bulk_create_products(self, products_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple products in bulk"""
        try:
            self.log_operation("bulk_create_products", {"count": len(products_data)})
            
            if not products_data:
                raise ValidationError("No products data provided")
            
            # Validate each product
            for i, product_data in enumerate(products_data):
                required_fields = ['name', 'sku']
                self.validate_required_fields(product_data, required_fields)
                
                # Check SKU uniqueness
                if self.product_repository.get_by_sku(product_data['sku']):
                    raise ValidationError(f"Product {i+1}: SKU '{product_data['sku']}' already exists")
                
                # Check barcode uniqueness if provided
                if product_data.get('barcode') and self.product_repository.get_by_barcode(product_data['barcode']):
                    raise ValidationError(f"Product {i+1}: Barcode '{product_data['barcode']}' already exists")
            
            # Sanitize all products
            sanitized_products = [self.sanitize_input(product_data) for product_data in products_data]
            
            # Create products in bulk
            created_products = self.product_repository.bulk_create(sanitized_products)
            
            self.log_operation("bulk_create_products_success", {"count": len(created_products)})
            
            return self.create_response(
                success=True,
                data=[product.to_dict() for product in created_products],
                message=f"Successfully created {len(created_products)} products"
            )
                
        except Exception as e:
            self.log_error("bulk_create_products", e, {"count": len(products_data)})
            if isinstance(e, ValidationError):
                return self.create_response(success=False, error=str(e))
            raise ServiceError(f"Failed to bulk create products: {str(e)}")
    
    def bulk_update_products(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update multiple products in bulk"""
        try:
            self.log_operation("bulk_update_products", {"count": len(updates)})
            
            if not updates:
                raise ValidationError("No product updates provided")
            
            # Validate each update
            for i, update_data in enumerate(updates):
                if 'id' not in update_data:
                    raise ValidationError(f"Update {i+1}: Product ID is required")
                
                # Check if product exists
                if not self.product_repository.exists(update_data['id']):
                    raise ValidationError(f"Update {i+1}: Product with ID '{update_data['id']}' not found")
            
            # Sanitize all updates
            sanitized_updates = [self.sanitize_input(update_data) for update_data in updates]
            
            # Update products in bulk
            updated_products = self.product_repository.bulk_update(sanitized_updates)
            
            self.log_operation("bulk_update_products_success", {"count": len(updated_products)})
            
            return self.create_response(
                success=True,
                data=[product.to_dict() for product in updated_products],
                message=f"Successfully updated {len(updated_products)} products"
            )
                
        except Exception as e:
            self.log_error("bulk_update_products", e, {"count": len(updates)})
            if isinstance(e, ValidationError):
                return self.create_response(success=False, error=str(e))
            raise ServiceError(f"Failed to bulk update products: {str(e)}")
    
    def bulk_delete_products(self, product_ids: List[str]) -> Dict[str, Any]:
        """Delete multiple products in bulk"""
        try:
            self.log_operation("bulk_delete_products", {"count": len(product_ids)})
            
            if not product_ids:
                raise ValidationError("No product IDs provided")
            
            # Check if all products exist
            for product_id in product_ids:
                if not self.product_repository.exists(product_id):
                    raise NotFoundError(f"Product with ID '{product_id}' not found")
            
            # Delete products in bulk
            deleted_count = self.product_repository.bulk_delete(product_ids)
            
            self.log_operation("bulk_delete_products_success", {"deleted_count": deleted_count})
            
            return self.create_response(
                success=True,
                data={"deleted_count": deleted_count},
                message=f"Successfully deleted {deleted_count} products"
            )
                
        except Exception as e:
            self.log_error("bulk_delete_products", e, {"count": len(product_ids)})
            if isinstance(e, (ValidationError, NotFoundError)):
                return self.create_response(success=False, error=str(e))
            raise ServiceError(f"Failed to bulk delete products: {str(e)}")
