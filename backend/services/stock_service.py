"""
Stock Service for Inventory Management System
Handles complex stock operations, business logic, and stock management workflows
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta, date

from backend.models.stock import StockItem, StockTransaction
from backend.models.product import Product
from backend.repositories.stock_repository import StockRepository
from backend.utils.database import execute_query

# Configure logging
logger = logging.getLogger(__name__)


class StockService:
    """Service class for stock management operations"""
    
    def __init__(self):
        """Initialize StockService with required repositories"""
        self.stock_repository = StockRepository()
    
    @staticmethod
    def handle_stock_receiving(product_id: str, bin_id: str, qty_available: int, 
                              qty_reserved: int = 0, batch_id: str = None, 
                              expiry_date: datetime = None, user_id: str = None) -> Dict[str, Any]:
        """
        Handle stock receiving with batch tracking logic.
        For non-batch-tracked products: combine stock in same bin
        For batch-tracked products: create separate inventory record
        """
        try:
            # Get product information to check if it's batch tracked
            product = Product.get_by_id(product_id)
            if not product:
                raise Exception("Product not found")
            
            is_batch_tracked = product.batch_tracked
            
            if is_batch_tracked:
                # For batch-tracked products, always create new record
                stock_item = StockItem.create(
                    product_id=product_id,
                    bin_id=bin_id,
                    on_hand=qty_available,
                    qty_reserved=qty_reserved,
                    batch_id=batch_id,
                    expiry_date=expiry_date
                )
                
                if not stock_item:
                    raise Exception("Failed to create stock item")
                
                # Log transaction
                StockTransaction.create(
                    stock_item_id=stock_item.id,
                    transaction_type='receive',
                    quantity_change=qty_available,
                    quantity_before=0,
                    quantity_after=qty_available,
                    notes=f"Stock received - Batch: {batch_id}" if batch_id else "Stock received",
                    user_id=user_id
                )
                
                return {'id': stock_item.id, 'action': 'created'}
            else:
                # For non-batch-tracked products, check if stock already exists in this bin
                existing_stock = StockItem.get_by_product_and_bin(product_id, bin_id)
                
                if existing_stock:
                    # Combine with existing stock
                    new_available = existing_stock.on_hand + qty_available
                    new_reserved = existing_stock.qty_reserved + qty_reserved
                    
                    success = existing_stock.update_stock(
                        on_hand=new_available,
                        qty_reserved=new_reserved
                    )
                    
                    if not success:
                        raise Exception("Failed to update existing stock")
                    
                    # Log transaction
                    StockTransaction.create(
                        stock_item_id=existing_stock.id,
                        transaction_type='receive',
                        quantity_change=qty_available,
                        quantity_before=existing_stock.on_hand,
                        quantity_after=new_available,
                        notes="Stock received - Combined with existing stock",
                        user_id=user_id
                    )
                    
                    return {'id': existing_stock.id, 'action': 'updated'}
                else:
                    # Create new stock record (no batch info for non-batch-tracked)
                    stock_item = StockItem.create(
                        product_id=product_id,
                        bin_id=bin_id,
                        on_hand=qty_available,
                        qty_reserved=qty_reserved,
                        batch_id=None,
                        expiry_date=None
                    )
                    
                    if not stock_item:
                        raise Exception("Failed to create stock item")
                    
                    # Log transaction
                    StockTransaction.create(
                        stock_item_id=stock_item.id,
                        transaction_type='receive',
                        quantity_change=qty_available,
                        quantity_before=0,
                        quantity_after=qty_available,
                        notes="Stock received - New stock item",
                        user_id=user_id
                    )
                    
                    return {'id': stock_item.id, 'action': 'created'}
                    
        except Exception as e:
            logger.error(f"Error handling stock receiving: {e}")
            raise e
    
    @staticmethod
    def log_stock_transaction(stock_item_id: str, transaction_type: str, 
                             quantity_change: int, quantity_before: int, 
                             quantity_after: int, reference_id: str = None, 
                             notes: str = None, user_id: str = None) -> Optional[StockTransaction]:
        """Log stock transaction for audit trail"""
        try:
            transaction = StockTransaction.create(
                stock_item_id=stock_item_id,
                transaction_type=transaction_type,
                quantity_change=quantity_change,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                notes=notes,
                user_id=user_id
            )
            
            if not transaction:
                logger.error(f"Failed to create stock transaction for stock item {stock_item_id}")
                return None
            
            logger.info(f"Stock transaction logged: {transaction_type} for stock item {stock_item_id}")
            return transaction
            
        except Exception as e:
            logger.error(f"Error logging stock transaction: {e}")
            return None
    
    @staticmethod
    def move_stock(source_stock_id: str, dest_bin_id: str, quantity: int, 
                   reserved_quantity: int = 0,
                   user_id: str = None, notes: str = None) -> Dict[str, Any]:
        """Move stock from one bin to another"""
        try:
            # Get source stock item
            source_stock = StockItem.get_by_id(source_stock_id)
            if not source_stock:
                raise Exception("Source stock item not found")
            
            if quantity < 0 or reserved_quantity < 0:
                raise Exception("Quantities must be non-negative")
            if source_stock.available_stock < quantity:
                raise Exception(f"Insufficient available stock. Available: {source_stock.available_stock}, Requested: {quantity}")
            if source_stock.qty_reserved < reserved_quantity:
                raise Exception(f"Insufficient reserved stock. Reserved: {source_stock.qty_reserved}, Requested: {reserved_quantity}")
            
            # Check if destination bin exists
            from backend.models.warehouse import Bin
            dest_bin = Bin.get_by_id(dest_bin_id)
            if not dest_bin:
                raise Exception("Destination bin not found")
            
            # Check if stock already exists in destination bin
            dest_stock = StockItem.get_by_product_and_bin(source_stock.product_id, dest_bin_id)
            
            # Calculate new quantities
            prev_source_on_hand = source_stock.on_hand
            prev_source_reserved = source_stock.qty_reserved
            new_source_on_hand = max(0, prev_source_on_hand - quantity)
            new_source_reserved = max(0, prev_source_reserved - reserved_quantity)
            new_source_available = max(0, new_source_on_hand - new_source_reserved)
            source_will_be_empty = new_source_available == 0
            
            # Update source stock
            # Always update source to reflect new on_hand (do not delete to preserve referential integrity)
            success = source_stock.update_stock(on_hand=new_source_on_hand, qty_reserved=new_source_reserved)
            if not success:
                raise Exception("Failed to update source stock")
            
            # Handle destination stock
            if dest_stock:
                # Add to existing stock in destination
                new_dest_on_hand = dest_stock.on_hand + quantity
                new_dest_reserved = (dest_stock.qty_reserved or 0) + reserved_quantity
                success = dest_stock.update_stock(on_hand=new_dest_on_hand, qty_reserved=new_dest_reserved)
                if not success:
                    raise Exception("Failed to update destination stock")
                dest_stock_id = dest_stock.id
            else:
                # Create new stock item in destination
                new_stock = StockItem.create(
                    product_id=source_stock.product_id,
                    bin_id=dest_bin_id,
                    on_hand=quantity,
                    qty_reserved=reserved_quantity,
                    batch_id=source_stock.batch_id,
                    expiry_date=source_stock.expiry_date
                )
                if not new_stock:
                    raise Exception("Failed to create destination stock item")
                dest_stock_id = new_stock.id
            
            # Log transactions
            transaction_notes = notes or f"Stock moved from bin {source_stock.bin_id} to {dest_bin_id}"
            
            # Source transaction
            if source_will_be_empty:
                StockService.log_stock_transaction(
                    stock_item_id=source_stock_id,
                    transaction_type='adjust',
                    quantity_change=-quantity,
                    quantity_before=prev_source_on_hand + prev_source_reserved,
                    quantity_after=0,
                    notes=transaction_notes + " (Deallocated)",
                    user_id=user_id
                )
            else:
                StockService.log_stock_transaction(
                    stock_item_id=source_stock_id,
                    transaction_type='transfer',
                    quantity_change=-quantity,
                    quantity_before=prev_source_on_hand + prev_source_reserved,
                    quantity_after=new_source_available + prev_source_reserved,
                    notes=transaction_notes,
                    user_id=user_id
                )
            
            # Destination transaction
            if dest_stock:
                dest_quantity_before = (dest_stock.on_hand or 0) + (dest_stock.qty_reserved or 0)
                dest_quantity_after = (dest_stock.on_hand or 0) + quantity + (dest_stock.qty_reserved or 0) + reserved_quantity
            else:
                dest_quantity_before = 0
                dest_quantity_after = quantity + reserved_quantity
            
            StockService.log_stock_transaction(
                stock_item_id=dest_stock_id,
                transaction_type='receive',
                quantity_change=quantity,
                quantity_before=dest_quantity_before,
                quantity_after=dest_quantity_after,
                notes=transaction_notes,
                user_id=user_id
            )
            
            return {
                'success': True,
                'source_stock_id': source_stock_id,
                'dest_stock_id': dest_stock_id,
                'quantity': quantity,
                'reserved_quantity': reserved_quantity,
                'source_deallocated': source_will_be_empty
            }
            
        except Exception as e:
            logger.error(f"Error moving stock: {e}")
            raise e
    
    @staticmethod
    def analyze_batch_data(batch_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze batch tracking data for insights"""
        try:
            today = datetime.now().date()
            total_batches = len(set(item['batch_id'] for item in batch_items if item.get('batch_id')))
            expiring_soon = 0
            expired = 0
            no_expiry = 0
            
            # Expiry timeline for chart (next 12 months)
            expiry_timeline = []
            for i in range(12):
                month_start = today + timedelta(days=30*i)
                month_end = today + timedelta(days=30*(i+1))
                month_name = month_start.strftime('%b %Y')
                
                count = 0
                for item in batch_items:
                    if item.get('expiry_date'):
                        try:
                            raw = item['expiry_date']
                            if isinstance(raw, str):
                                expiry_date = datetime.strptime(raw, '%Y-%m-%d').date()
                            elif isinstance(raw, datetime):
                                expiry_date = raw.date()
                            elif isinstance(raw, date):
                                expiry_date = raw
                            else:
                                continue
                            if month_start <= expiry_date < month_end:
                                count += 1
                        except (ValueError, TypeError):
                            pass
                
                expiry_timeline.append({'month': month_name, 'count': count})
            
            # Count categories
            for item in batch_items:
                if not item.get('expiry_date'):
                    no_expiry += 1
                else:
                    try:
                        raw = item['expiry_date']
                        if isinstance(raw, str):
                            expiry_date = datetime.strptime(raw, '%Y-%m-%d').date()
                        elif isinstance(raw, datetime):
                            expiry_date = raw.date()
                        elif isinstance(raw, date):
                            expiry_date = raw
                        else:
                            no_expiry += 1
                            continue
                        days_to_expiry = (expiry_date - today).days
                        if days_to_expiry < 0:
                            expired += 1
                        elif days_to_expiry <= 30:
                            expiring_soon += 1
                    except (ValueError, TypeError):
                        no_expiry += 1
            
            return {
                'total_batches': total_batches,
                'expiring_soon': expiring_soon,
                'expired': expired,
                'no_expiry': no_expiry,
                'expiry_timeline': expiry_timeline
            }
            
        except Exception as e:
            logger.error(f"Error analyzing batch data: {e}")
            return {
                'total_batches': 0,
                'expiring_soon': 0,
                'expired': 0,
                'no_expiry': 0,
                'expiry_timeline': []
            }
    
    @staticmethod
    def get_stock_summary(product_id: str = None) -> Dict[str, Any]:
        """Get comprehensive stock summary"""
        try:
            if product_id:
                # Get stock for specific product
                stock_items = StockItem.get_by_product(product_id)
                product = Product.get_by_id(product_id)
                product_name = product.name if product else "Unknown Product"
            else:
                # Get all stock items
                stock_items = []
                products = Product.get_all()
                for product in products:
                    stock_items.extend(StockItem.get_by_product(product.id))
                product_name = "All Products"
            
            total_on_hand = sum((item.on_hand or 0) for item in stock_items)
            total_reserved = sum((item.qty_reserved or 0) for item in stock_items)
            total_available = sum(((item.on_hand or 0) - (item.qty_reserved or 0)) for item in stock_items)

            # Count low stock items using a simple threshold on available
            LOW_STOCK_THRESHOLD = 5
            low_stock_count = sum(1 for item in stock_items if ((item.on_hand or 0) - (item.qty_reserved or 0)) <= LOW_STOCK_THRESHOLD)

            # Count expired items safely
            expired_count = 0
            today = datetime.now().date()
            for item in stock_items:
                raw = getattr(item, 'expiry_date', None)
                if not raw:
                    continue
                try:
                    if isinstance(raw, str):
                        exp = datetime.strptime(raw, '%Y-%m-%d').date()
                    elif isinstance(raw, datetime):
                        exp = raw.date()
                    elif isinstance(raw, date):
                        exp = raw
                    else:
                        continue
                    if exp < today:
                        expired_count += 1
                except Exception:
                    continue
            
            return {
                'product_name': product_name,
                'total_stock_items': len(stock_items),
                'total_on_hand': total_on_hand,
                'total_reserved': total_reserved,
                'total_available': total_available,
                'low_stock_count': low_stock_count,
                'expired_count': expired_count
            }
            
        except Exception as e:
            logger.error(f"Error getting stock summary: {e}")
            return {
                'product_name': "Error",
                'total_stock_items': 0,
                'total_on_hand': 0,
                'total_reserved': 0,
                'total_available': 0,
                'low_stock_count': 0,
                'expired_count': 0
            }
    
    @staticmethod
    def reserve_stock(stock_item_id: str, quantity: int, user_id: str = None) -> bool:
        """Reserve stock quantity"""
        try:
            repo = StockRepository()
            return repo.reserve_stock(stock_item_id, quantity, user_id)
            
        except Exception as e:
            logger.error(f"Error reserving stock: {e}")
            return False
    
    @staticmethod
    def release_reserved_stock(stock_item_id: str, quantity: int, user_id: str = None) -> bool:
        """Release reserved stock quantity"""
        try:
            repo = StockRepository()
            return repo.release_stock(stock_item_id, quantity, user_id)
            
        except Exception as e:
            logger.error(f"Error releasing reserved stock: {e}")
            return False
    
    def get_stock_by_product(self, product_id: str) -> List[Dict[str, Any]]:
        """Get stock items for a specific product"""
        try:
            return self.stock_repository.get_stock_by_product(product_id)
        except Exception as e:
            logger.error(f"Error getting stock by product: {e}")
            return []
    
    def get_stock_by_warehouse(self, warehouse_id: str) -> List[Dict[str, Any]]:
        """Get stock items in a specific warehouse"""
        try:
            return self.stock_repository.get_stock_by_warehouse(warehouse_id)
        except Exception as e:
            logger.error(f"Error getting stock by warehouse: {e}")
            return []
    
    def get_low_stock_items(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """Get stock items below threshold"""
        try:
            return self.stock_repository.get_low_stock_items(threshold)
        except Exception as e:
            logger.error(f"Error getting low stock items: {e}")
            return []
    
    def get_expiring_stock(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get stock items expiring soon"""
        try:
            return self.stock_repository.get_expiring_stock(days_ahead)
        except Exception as e:
            logger.error(f"Error getting expiring stock: {e}")
            return []
