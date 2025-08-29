"""
Product Service for Inventory Management System
Handles product-related business logic and operations
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta

from models.product import Product
from models.stock import StockItem
from utils.database import execute_query

# Configure logging
logger = logging.getLogger(__name__)


class ProductService:
    """Service class for product management operations"""
    
    @staticmethod
    def create_product(name: str, description: str = None, sku: str = None,
                       barcode: str = None, dimensions: str = None, weight: float = None,
                       picture_url: str = None, batch_tracked: bool = False) -> Optional[Product]:
        """Create a new product with validation"""
        try:
            # Validate required fields
            if not name or not name.strip():
                raise ValueError("Product name is required")
            
            # Check for duplicate SKU if provided
            if sku:
                existing_product = Product.search(sku)
                if existing_product:
                    raise ValueError(f"Product with SKU '{sku}' already exists")
            
            # Check for duplicate barcode if provided
            if barcode:
                existing_product = Product.get_by_barcode(barcode)
                if existing_product:
                    raise ValueError(f"Product with barcode '{barcode}' already exists")
            
            # Create the product
            product = Product.create(
                name=name.strip(),
                description=description.strip() if description else None,
                sku=sku.strip() if sku else None,
                barcode=barcode.strip() if barcode else None,
                dimensions=dimensions.strip() if dimensions else None,
                weight=weight,
                picture_url=picture_url.strip() if picture_url else None,
                batch_tracked=batch_tracked
            )
            
            if product:
                logger.info(f"Product '{name}' created successfully with ID {product.id}")
                return product
            else:
                logger.error(f"Failed to create product '{name}'")
                return None
                
        except Exception as e:
            logger.error(f"Error creating product '{name}': {e}")
            raise e
    
    @staticmethod
    def update_product(product_id: str, **kwargs) -> bool:
        """Update product with validation"""
        try:
            product = Product.get_by_id(product_id)
            if not product:
                raise ValueError("Product not found")
            
            # Validate SKU uniqueness if being updated
            if 'sku' in kwargs and kwargs['sku']:
                existing_products = Product.search(kwargs['sku'])
                for existing in existing_products:
                    if existing.id != product_id:
                        raise ValueError(f"Product with SKU '{kwargs['sku']}' already exists")
            
            # Validate barcode uniqueness if being updated
            if 'barcode' in kwargs and kwargs['barcode']:
                existing_product = Product.get_by_barcode(kwargs['barcode'])
                if existing_product and existing_product.id != product_id:
                    raise ValueError(f"Product with barcode '{kwargs['barcode']}' already exists")
            
            # Clean up string fields
            for key in ['name', 'description', 'sku', 'barcode', 'dimensions', 'picture_url']:
                if key in kwargs and kwargs[key]:
                    kwargs[key] = kwargs[key].strip()
            
            # Update the product
            success = product.update(**kwargs)
            
            if success:
                logger.info(f"Product {product_id} updated successfully")
                return True
            else:
                logger.error(f"Failed to update product {product_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            raise e
    
    @staticmethod
    def delete_product(product_id: str) -> bool:
        """Delete product with validation"""
        try:
            product = Product.get_by_id(product_id)
            if not product:
                raise ValueError("Product not found")
            
            # Check if product has stock
            stock_items = StockItem.get_by_product(product_id)
            if stock_items:
                total_stock = sum(item.on_hand for item in stock_items)
                if total_stock > 0:
                    raise ValueError(f"Cannot delete product with {total_stock} units in stock")
            
            # Delete the product
            success = product.delete()
            
            if success:
                logger.info(f"Product {product_id} deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete product {product_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting product {product_id}: {e}")
            raise e
    
    @staticmethod
    def get_product_details(product_id: str) -> Dict[str, Any]:
        """Get comprehensive product details including stock information"""
        logger.info(f"ProductService.get_product_details called with product_id: {product_id}")
        logger.info(f"Product ID type: {type(product_id)}")
        try:
            product = Product.get_by_id(product_id)
            if not product:
                return {'error': 'Product not found'}
            
            # Get stock information
            stock_items = StockItem.get_by_product(product_id)
            stock_levels = product.get_stock_levels()
            
            # Get stock by location with full hierarchy
            stock_locations = []
            for item in stock_items:
                from models.warehouse import Bin, Location, Warehouse
                bin_obj = Bin.get_by_id(item.bin_id)
                if bin_obj:
                    location_obj = None
                    warehouse_obj = None
                    
                    if bin_obj.location_id:
                        location_obj = Location.get_by_id(bin_obj.location_id)
                        if location_obj and location_obj.warehouse_id:
                            warehouse_obj = Warehouse.get_by_id(location_obj.warehouse_id)
                    
                    stock_locations.append({
                        'warehouse_name': warehouse_obj.name if warehouse_obj else 'Unknown',
                        'warehouse_address': warehouse_obj.address if warehouse_obj else 'Unknown',
                        'aisle': location_obj.full_code if location_obj else 'Unknown',
                        'bin': bin_obj.code,
                        'on_hand': item.on_hand,
                        'qty_reserved': item.qty_reserved,
                        'available': item.available_stock,
                        'batch_id': item.batch_id,
                        'expiry_date': item.expiry_date.isoformat() if item.expiry_date else None,
                        'created_at': item.created_at.isoformat() if item.created_at else None
                    })
            
            # Get recent transactions
            transaction_history = []
            for item in stock_items[:5]:  # Limit to 5 most recent items
                from models.stock import StockTransaction
                transactions = StockTransaction.get_by_stock_item(item.id, limit=20)
                for txn in transactions:
                    transaction_history.append({
                        'transaction_type': txn.transaction_type,
                        'quantity_change': txn.quantity_change,
                        'quantity_before': txn.quantity_before,
                        'quantity_after': txn.quantity_after,
                        'created_at': txn.created_at.isoformat() if txn.created_at else None,
                        'notes': txn.notes,
                        'user_name': 'System'  # TODO: Get actual user name
                    })
            
            # Sort transactions by date (most recent first)
            transaction_history.sort(key=lambda x: x['created_at'], reverse=True)
            transaction_history = transaction_history[:100]  # Limit to 100 transactions
            
            # Calculate forecasting data (simplified)
            current_stock = stock_levels['total_available']
            avg_daily_usage = 0  # TODO: Calculate from transaction history
            lead_time_days = 7  # Default
            safety_stock = max(5, int(avg_daily_usage * lead_time_days * 0.5))
            reorder_point = safety_stock + int(avg_daily_usage * lead_time_days)
            days_of_stock = current_stock / avg_daily_usage if avg_daily_usage > 0 else float('inf')
            
            # Determine stock status
            stock_status = 'low' if current_stock <= reorder_point else 'ok'
            
            # Get warehouse distribution
            warehouse_distribution = {}
            for location in stock_locations:
                warehouse_name = location['warehouse_name']
                if warehouse_name not in warehouse_distribution:
                    warehouse_distribution[warehouse_name] = 0
                warehouse_distribution[warehouse_name] += location['available']
            
            warehouse_distribution_list = [
                {'warehouse_name': name, 'total_available': qty}
                for name, qty in warehouse_distribution.items()
            ]
            
            # Generate stock trends (simplified - last 30 days)
            stock_trends = []
            for i in range(30):
                # TODO: Calculate actual trends from transaction history
                stock_trends.append({
                    'date': (datetime.now() - timedelta(days=29-i)).isoformat(),
                    'received': 0,
                    'shipped': 0,
                    'adjusted': 0
                })
            
            # Get expiring items
            expiring_alerts = []
            for item in stock_items:
                if item.expiry_date and item.days_until_expiry() is not None:
                    days_until_expiry = item.days_until_expiry()
                    if days_until_expiry <= 30:  # Alert for items expiring within 30 days
                        expiring_alerts.append({
                            'batch_id': item.batch_id,
                            'expiry_date': item.expiry_date.isoformat(),
                            'on_hand': item.on_hand,
                            'warehouse_name': 'Unknown',  # TODO: Get from location
                            'full_code': 'Unknown'  # TODO: Get from location
                        })
            
            return {
                'product': product.to_dict(),
                'summary': {
                    'total_locations': len(stock_locations),
                    'total_transactions': len(transaction_history)
                },
                'stock_locations': stock_locations,
                'transaction_history': transaction_history,
                'forecasting': {
                    'current_stock': current_stock,
                    'avg_daily_usage': avg_daily_usage,
                    'usage_std_dev': 0,  # TODO: Calculate
                    'max_daily_usage': 0,  # TODO: Calculate
                    'lead_time_days': lead_time_days,
                    'safety_stock': safety_stock,
                    'reorder_point': reorder_point,
                    'days_of_stock': days_of_stock,
                    'stock_status': stock_status,
                    'calculation_mode': 'Automatic'
                },
                'warehouse_distribution': warehouse_distribution_list,
                'stock_trends': stock_trends,
                'expiry_alerts': expiring_alerts
            }
            
        except Exception as e:
            logger.error(f"Error getting product details for {product_id}: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def search_products(search_term: str, batch_tracked: bool = None) -> List[Product]:
        """Search products with filters"""
        try:
            products = Product.search(search_term)
            
            # Apply filters
            if batch_tracked is not None:
                products = [p for p in products if p.batch_tracked == batch_tracked]
            
            return products
            
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []
    
    @staticmethod
    def get_low_stock_products() -> List[Dict[str, Any]]:
        """Get products with low stock levels"""
        try:
            products = Product.get_all()
            low_stock_products = []
            
            for product in products:
                if product.is_low_stock():
                    stock_levels = product.get_stock_levels()
                    low_stock_products.append({
                        'product': product.to_dict(),
                        'stock_levels': stock_levels,
                        'shortfall': 5 - stock_levels['total_available']  # Default threshold is 5
                    })
            
            # Sort by shortfall (highest first)
            low_stock_products.sort(key=lambda x: x['shortfall'], reverse=True)
            return low_stock_products
            
        except Exception as e:
            logger.error(f"Error getting low stock products: {e}")
            return []
    
    @staticmethod
    def get_overstocked_products() -> List[Dict[str, Any]]:
        """Get products that are overstocked"""
        try:
            products = Product.get_all()
            overstocked_products = []
            
            for product in products:
                if product.is_overstocked():
                    stock_levels = product.get_stock_levels()
                    overstocked_products.append({
                        'product': product.to_dict(),
                        'stock_levels': stock_levels,
                        'excess': stock_levels['total_available'] - 100  # Default threshold is 100
                    })
            
            # Sort by excess (highest first)
            overstocked_products.sort(key=lambda x: x['excess'], reverse=True)
            return overstocked_products
            
        except Exception as e:
            logger.error(f"Error getting overstocked products: {e}")
            return []
    
    @staticmethod
    def get_expiring_products(days_threshold: int = 30) -> List[Dict[str, Any]]:
        """Get products with items expiring soon"""
        try:
            products = Product.get_all()
            expiring_products = []
            
            for product in products:
                if product.batch_tracked:
                    stock_items = StockItem.get_by_product(product.id)
                    expiring_items = []
                    
                    for item in stock_items:
                        if item.expiry_date:
                            days_until_expiry = item.days_until_expiry()
                            if days_until_expiry is not None and days_until_expiry <= days_threshold:
                                expiring_items.append({
                                    'stock_item_id': item.id,
                                    'batch_id': item.batch_id,
                                    'quantity': item.on_hand,
                                    'expiry_date': item.expiry_date.isoformat(),
                                    'days_until_expiry': days_until_expiry
                                })
                    
                    if expiring_items:
                        expiring_products.append({
                            'product': product.to_dict(),
                            'expiring_items': expiring_items
                        })
            
            return expiring_products
            
        except Exception as e:
            logger.error(f"Error getting expiring products: {e}")
            return []
    
    @staticmethod
    def generate_product_report() -> Dict[str, Any]:
        """Generate comprehensive product report"""
        try:
            products = Product.get_all()
            total_products = len(products)
            
            # Categorize products
            batch_tracked_count = sum(1 for p in products if p.batch_tracked)
            non_batch_tracked_count = total_products - batch_tracked_count
            
            # Stock status
            low_stock_count = len(ProductService.get_low_stock_products())
            overstocked_count = len(ProductService.get_overstocked_products())
            expiring_count = len(ProductService.get_expiring_products())
            
            return {
                'total_products': total_products,
                'batch_tracked': batch_tracked_count,
                'non_batch_tracked': non_batch_tracked_count,
                'low_stock_count': low_stock_count,
                'overstocked_count': overstocked_count,
                'expiring_count': expiring_count,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating product report: {e}")
            return {'error': str(e)}
