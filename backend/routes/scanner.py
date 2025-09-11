"""
Scanner Routes for Inventory Management System
Handles barcode scanner functionality and operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import logging

from backend.services.stock_service import StockService
from backend.models.product import Product
from backend.models.warehouse import Bin, Location, Warehouse
from backend.models.stock import StockItem

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
scanner_bp = Blueprint('scanner', __name__, url_prefix='/scanner')


@scanner_bp.route('/')
@login_required
def scanner_page():
    """Main scanner page"""
    try:
        return render_template('scanner.html')
        
    except Exception as e:
        logger.error(f"Error loading scanner page: {e}")
        flash('Error loading scanner page. Please try again.', 'error')
        return render_template('error.html', message='Scanner page unavailable')


@scanner_bp.route('/barcode-scanner')
@login_required
def barcode_scanner():
    """Barcode scanner interface"""
    try:
        return render_template('barcode_scanner.html')
        
    except Exception as e:
        logger.error(f"Error loading barcode scanner: {e}")
        flash('Error loading barcode scanner. Please try again.', 'error')
        return redirect(url_for('scanner.scanner_page'))


# API Routes for Scanner
@scanner_bp.route('/api/location/<location_code>')
@login_required
def api_get_location(location_code):
    """API endpoint to get location by code"""
    try:
        location = Location.get_by_code(location_code)
        if not location:
            return jsonify({
                'success': False,
                'error': 'Location not found'
            }), 404
        
        # Get warehouse info
        warehouse = Warehouse.get_by_id(location.warehouse_id)
        
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
        
        return jsonify({
            'success': True,
            'location': {
                'id': location.id,
                'code': location.code,
                'name': location.name,
                'description': location.description,
                'warehouse': warehouse.to_dict() if warehouse else None,
                'bins': bins_data
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting location {location_code}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get location information'
        }), 500


@scanner_bp.route('/api/bin/<bin_code>')
@login_required
def api_get_bin(bin_code):
    """API endpoint to get bin by code"""
    try:
        bin_obj = Bin.get_by_code(bin_code)
        if not bin_obj:
            return jsonify({
                'success': False,
                'error': 'Bin not found'
            }), 404
        
        # Get location and warehouse info
        location = Location.get_by_id(bin_obj.location_id)
        warehouse = None
        try:
            from backend.models.warehouse import Warehouse as _Warehouse
            if location and getattr(location, 'warehouse_id', None):
                warehouse = _Warehouse.get_by_id(location.warehouse_id)
        except Exception:
            warehouse = None
        
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
                    'expiry_date': item.expiry_date.isoformat() if item.expiry_date else None,
                    'days_until_expiry': item.days_until_expiry()
                })
        
        return jsonify({
            'success': True,
            'bin': {
                'id': bin_obj.id,
                'code': bin_obj.code,
                'name': bin_obj.name,
                'description': bin_obj.description,
                'capacity': bin_obj.capacity,
                'location': location.to_dict() if location else None,
                'warehouse': warehouse.to_dict() if warehouse else None,
                'stock_items': stock_data,
                'total_stock': sum(item.on_hand for item in stock_items),
                'utilization_percentage': (sum(item.on_hand for item in stock_items) / bin_obj.capacity * 100) if bin_obj.capacity > 0 else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting bin {bin_code}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get bin information'
        }), 500


@scanner_bp.route('/api/transaction', methods=['POST'])
@login_required
def api_scanner_transaction():
    """API endpoint for scanner transactions"""
    try:
        data = request.get_json()
        transaction_type = data.get('type')
        
        if transaction_type == 'stock_receive':
            # Handle stock receiving
            result = StockService.handle_stock_receiving(
                product_id=data.get('product_id'),
                bin_id=data.get('bin_id'),
                qty_available=data.get('quantity', 0),
                qty_reserved=data.get('reserved', 0),
                batch_id=data.get('batch_id'),
                expiry_date=data.get('expiry_date'),
                user_id=current_user.id
            )
            
            if result:
                return jsonify({
                    'success': True,
                    'result': result,
                    'message': 'Stock received successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to receive stock'
                }), 400
                
        elif transaction_type == 'stock_move':
            # Handle stock movement
            result = StockService.move_stock(
                source_stock_id=data.get('source_stock_id'),
                dest_bin_id=data.get('dest_bin_id'),
                quantity=data.get('quantity', 0),
                reserved_quantity=data.get('reserved_quantity', 0),
                user_id=current_user.id,
                notes=data.get('notes')
            )
            
            if result and result.get('success'):
                return jsonify({
                    'success': True,
                    'result': result,
                    'message': 'Stock moved successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to move stock'
                }), 400
                
        elif transaction_type == 'reserve':
            # Reserve stock on a specific stock item
            stock_item_id = data.get('stock_item_id')
            quantity = data.get('quantity') or data.get('quantity_change') or 0
            try:
                quantity = int(quantity)
            except Exception:
                quantity = 0
            if not stock_item_id or quantity <= 0:
                return jsonify({'success': False, 'error': 'stock_item_id and positive quantity are required'}), 400
            success = StockService.reserve_stock(stock_item_id, quantity, current_user.id)
            if success:
                return jsonify({'success': True, 'message': 'Stock reserved', 'transaction': {'type': 'reserve', 'quantity_change': quantity}})
            return jsonify({'success': False, 'error': 'Failed to reserve stock'}), 400

        elif transaction_type == 'release':
            # Release reserved stock from a specific stock item
            stock_item_id = data.get('stock_item_id')
            quantity = data.get('quantity') or data.get('quantity_change') or 0
            try:
                quantity = int(quantity)
            except Exception:
                quantity = 0
            if not stock_item_id or quantity <= 0:
                return jsonify({'success': False, 'error': 'stock_item_id and positive quantity are required'}), 400
            success = StockService.release_reserved_stock(stock_item_id, quantity, current_user.id)
            if success:
                return jsonify({'success': True, 'message': 'Reserved stock released', 'transaction': {'type': 'release', 'quantity_change': quantity}})
            return jsonify({'success': False, 'error': 'Failed to release reserved stock'}), 400

        elif transaction_type == 'bin_assign':
            # Handle bin assignment
            bin_code = data.get('bin_code')
            product_id = data.get('product_id')
            quantity = data.get('quantity', 0)
            
            bin_obj = Bin.get_by_code(bin_code)
            if not bin_obj:
                return jsonify({
                    'success': False,
                    'error': 'Bin not found'
                }), 404
            
            # Check if product exists
            product = Product.get_by_id(product_id)
            if not product:
                return jsonify({
                    'success': False,
                    'error': 'Product not found'
                }), 404
            
            # Create stock item in bin
            result = StockService.handle_stock_receiving(
                product_id=product_id,
                bin_id=bin_obj.id,
                qty_available=quantity,
                user_id=current_user.id
            )
            
            if result:
                return jsonify({
                    'success': True,
                    'result': result,
                    'message': 'Stock assigned to bin successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to assign stock to bin'
                }), 400
                
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid transaction type'
            }), 400
            
    except Exception as e:
        logger.error(f"Error in scanner transaction: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to process transaction'
        }), 500


@scanner_bp.route('/api/bin/<bin_code>/assign-stock', methods=['POST'])
@login_required
def api_assign_stock_to_bin(bin_code):
    """API endpoint to assign stock to a specific bin"""
    try:
        data = request.get_json()
        
        bin_obj = Bin.get_by_code(bin_code)
        if not bin_obj:
            return jsonify({
                'success': False,
                'error': 'Bin not found'
            }), 404
        
        # Get stock information
        product_id = data.get('product_id')
        quantity = data.get('quantity', 0)
        reserved = data.get('reserved', 0)
        batch_id = data.get('batch_id')
        expiry_date = data.get('expiry_date')
        
        # Validate inputs
        if not product_id or quantity <= 0:
            return jsonify({
                'success': False,
                'error': 'Product ID and valid quantity are required'
            }), 400
        
        # Check bin capacity
        current_stock = sum(item.on_hand for item in StockItem.get_by_bin(bin_obj.id))
        if current_stock + quantity > bin_obj.capacity:
            return jsonify({
                'success': False,
                'error': f'Bin capacity exceeded. Available: {bin_obj.capacity - current_stock}'
            }), 400
        
        # Assign stock to bin
        result = StockService.handle_stock_receiving(
            product_id=product_id,
            bin_id=bin_obj.id,
            qty_available=quantity,
            qty_reserved=reserved,
            batch_id=batch_id,
            expiry_date=expiry_date,
            user_id=current_user.id
        )
        
        if result:
            return jsonify({
                'success': True,
                'result': result,
                'message': 'Stock assigned to bin successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to assign stock to bin'
            }), 400
            
    except Exception as e:
        logger.error(f"Error assigning stock to bin {bin_code}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to assign stock to bin'
        }), 500


@scanner_bp.route('/api/bin/<bin_code>/change-location', methods=['POST'])
@login_required
def api_change_bin_location(bin_code):
    """API endpoint to change bin location"""
    try:
        data = request.get_json()
        new_location_id = data.get('location_id')
        
        bin_obj = Bin.get_by_code(bin_code)
        if not bin_obj:
            return jsonify({
                'success': False,
                'error': 'Bin not found'
            }), 404
        
        # Check if new location exists
        new_location = Location.get_by_id(new_location_id)
        if not new_location:
            return jsonify({
                'success': False,
                'error': 'New location not found'
            }), 404
        
        # Update bin location
        success = bin_obj.update(location_id=new_location_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Bin location changed successfully',
                'bin': bin_obj.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to change bin location'
            }), 400
            
    except Exception as e:
        logger.error(f"Error changing bin location for {bin_code}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to change bin location'
        }), 500


@scanner_bp.route('/api/locations/available')
@login_required
def api_available_locations():
    """API endpoint to get available locations"""
    try:
        locations = Location.get_all()
        
        return jsonify({
            'success': True,
            'locations': [loc.to_dict() for loc in locations]
        })
        
    except Exception as e:
        logger.error(f"Error getting available locations: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get available locations'
        }), 500


@scanner_bp.route('/api/bins/available')
@login_required
def api_available_bins():
    """API endpoint to get available bins"""
    try:
        bins = Bin.get_all()
        
        # Add location and warehouse info to each bin
        bins_data = []
        for bin_obj in bins:
            location = Location.get_by_id(bin_obj.location_id)
            warehouse = None
            try:
                from backend.models.warehouse import Warehouse as _Warehouse
                if location and getattr(location, 'warehouse_id', None):
                    warehouse = _Warehouse.get_by_id(location.warehouse_id)
            except Exception:
                warehouse = None

            bin_data = bin_obj.to_dict()
            bin_data['location'] = location.to_dict() if location else None
            bin_data['warehouse'] = warehouse.to_dict() if warehouse else None
            
            bins_data.append(bin_data)
        
        return jsonify({
            'success': True,
            'bins': bins_data
        })
        
    except Exception as e:
        logger.error(f"Error getting available bins: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get available bins'
        }), 500


@scanner_bp.route('/api/products/available')
@login_required
def api_available_products():
    """API endpoint to get available products"""
    try:
        products = Product.get_all()
        
        return jsonify({
            'success': True,
            'products': [product.to_dict() for product in products]
        })
        
    except Exception as e:
        logger.error(f"Error getting available products: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get available products'
        }), 500


@scanner_bp.route('/api/move-stock', methods=['POST'])
@login_required
def api_move_stock():
    """API endpoint for moving stock via scanner"""
    try:
        data = request.get_json()
        
        result = StockService.move_stock(
            source_stock_id=data.get('source_stock_id'),
            dest_bin_id=data.get('dest_bin_id'),
            quantity=data.get('quantity', 0),
            user_id=current_user.id,
            notes=data.get('notes', 'Stock moved via scanner')
        )
        
        if result and result.get('success'):
            return jsonify({
                'success': True,
                'result': result,
                'message': 'Stock moved successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to move stock'
            }), 400
            
    except Exception as e:
        logger.error(f"Error moving stock via scanner: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to move stock'
        }), 500


# Import required models (already imported at top)
