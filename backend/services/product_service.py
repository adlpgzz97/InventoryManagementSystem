"""
Product Service for Inventory Management System
Handles product-related business logic and operations
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from models.product import Product
from models.stock import StockItem
from utils.database import execute_query

# Configure logging
logger = logging.getLogger(__name__)


class ProductService:
    """Service class for product management operations"""
    
    @staticmethod
    def create_product(name: str, description: str = None, sku: str = None,
                       barcode: str = None, category: str = None, unit: str = None,
                       batch_tracked: bool = False, min_stock_level: int = 0,
                       max_stock_level: int = None) -> Optional[Product]:
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
                category=category.strip() if category else None,
                unit=unit.strip() if unit else None,
                batch_tracked=batch_tracked,
                min_stock_level=max(0, min_stock_level),
                max_stock_level=max_stock_level if max_stock_level and max_stock_level > 0 else None
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
            for key in ['name', 'description', 'sku', 'barcode', 'category', 'unit']:
                if key in kwargs and kwargs[key]:
                    kwargs[key] = kwargs[key].strip()
            
            # Validate numeric fields
            if 'min_stock_level' in kwargs:
                kwargs['min_stock_level'] = max(0, kwargs['min_stock_level'])
            
            if 'max_stock_level' in kwargs:
                kwargs['max_stock_level'] = kwargs['max_stock_level'] if kwargs['max_stock_level'] and kwargs['max_stock_level'] > 0 else None
            
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
        try:
            product = Product.get_by_id(product_id)
            if not product:
                return {'error': 'Product not found'}
            
            # Get stock information
            stock_items = StockItem.get_by_product(product_id)
            stock_levels = product.get_stock_levels()
            
            # Get stock by location
            stock_by_location = {}
            for item in stock_items:
                from models.warehouse import Bin
                bin_obj = Bin.get_by_id(item.bin_id)
                if bin_obj:
                    location_key = f"{bin_obj.bin_code}"
                    if location_key not in stock_by_location:
                        stock_by_location[location_key] = {
                            'bin_code': bin_obj.bin_code,
                            'on_hand': 0,
                            'reserved': 0,
                            'available': 0,
                            'batch_items': []
                        }
                    
                    stock_by_location[location_key]['on_hand'] += item.on_hand
                    stock_by_location[location_key]['reserved'] += item.qty_reserved
                    stock_by_location[location_key]['available'] += item.available_stock
                    
                    if item.batch_id:
                        stock_by_location[location_key]['batch_items'].append({
                            'batch_id': item.batch_id,
                            'quantity': item.on_hand,
                            'expiry_date': item.expiry_date.isoformat() if item.expiry_date else None,
                            'days_until_expiry': item.days_until_expiry()
                        })
            
            # Get recent transactions
            recent_transactions = []
            for item in stock_items[:5]:  # Limit to 5 most recent items
                transactions = StockItem.get_by_id(item.id)
                if transactions:
                    recent_transactions.extend(transactions)
            
            return {
                'product': product.to_dict(),
                'stock_summary': stock_levels,
                'stock_by_location': list(stock_by_location.values()),
                'recent_transactions': recent_transactions[:10],  # Limit to 10 transactions
                'alerts': {
                    'low_stock': product.is_low_stock(),
                    'overstocked': product.is_overstocked(),
                    'expired_items': sum(1 for item in stock_items if item.is_expired())
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting product details for {product_id}: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def search_products(search_term: str, category: str = None, 
                       batch_tracked: bool = None) -> List[Product]:
        """Search products with filters"""
        try:
            products = Product.search(search_term)
            
            # Apply filters
            if category:
                products = [p for p in products if p.category and p.category.lower() == category.lower()]
            
            if batch_tracked is not None:
                products = [p for p in products if p.batch_tracked == batch_tracked]
            
            return products
            
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []
    
    @staticmethod
    def get_product_categories() -> List[str]:
        """Get all product categories"""
        try:
            products = Product.get_all()
            categories = set()
            
            for product in products:
                if product.category:
                    categories.add(product.category)
            
            return sorted(list(categories))
            
        except Exception as e:
            logger.error(f"Error getting product categories: {e}")
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
                        'shortfall': product.min_stock_level - stock_levels['available_stock']
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
                        'excess': stock_levels['available_stock'] - product.max_stock_level
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
            
            # Category breakdown
            categories = ProductService.get_product_categories()
            category_breakdown = {}
            for category in categories:
                category_breakdown[category] = len([p for p in products if p.category == category])
            
            return {
                'total_products': total_products,
                'batch_tracked': batch_tracked_count,
                'non_batch_tracked': non_batch_tracked_count,
                'low_stock_count': low_stock_count,
                'overstocked_count': overstocked_count,
                'expiring_count': expiring_count,
                'category_breakdown': category_breakdown,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating product report: {e}")
            return {'error': str(e)}
