"""
Stock Routes for Inventory Management System
Handles stock management pages and operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import logging

from backend.services.stock_service import StockService
from backend.models.stock import StockItem, StockTransaction
from backend.models.product import Product
from backend.models.warehouse import Bin

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
stock_bp = Blueprint('stock', __name__, url_prefix='/stock')


@stock_bp.route('/')
@login_required
def stock_list():
    """Stock listing page"""
    try:
        # Get filter parameters
        product_id = request.args.get('product_id', '')
        bin_id = request.args.get('bin_id', '')
        warehouse_id = request.args.get('warehouse', '')
        filter_type = request.args.get('filter', '')
        
        # Get stock items based on filters
        if product_id:
            # For specific product, we need to get basic stock items and enhance them
            basic_stock_items = StockItem.get_by_product(product_id)
            stock_items = []
            for item in basic_stock_items:
                # Get enhanced data for each item
                enhanced_items = StockItem.get_all_with_locations()
                stock_items.extend([item for item in enhanced_items if item['product_id'] == product_id])
        elif bin_id:
            # For specific bin, we need to get basic stock items and enhance them
            basic_stock_items = StockItem.get_by_bin(bin_id)
            stock_items = []
            for item in basic_stock_items:
                # Get enhanced data for each item
                enhanced_items = StockItem.get_all_with_locations()
                stock_items.extend([item for item in enhanced_items if item['bin_id'] == bin_id])
        elif warehouse_id:
            # For specific warehouse, filter stock items by warehouse
            stock_items = StockItem.get_all_with_locations()
            stock_items = [item for item in stock_items if item.get('warehouse_id') == warehouse_id]
        elif filter_type == 'low_stock':
            # For low stock filter, get all items and filter
            stock_items = StockItem.get_all_with_locations()
            stock_items = [item for item in stock_items if item['available_stock'] <= 5]
        elif filter_type == 'expired':
            # For expired filter, get all items and filter
            stock_items = StockItem.get_all_with_locations()
            from datetime import datetime
            stock_items = [item for item in stock_items if item['expiry_date'] and datetime.now().date() > item['expiry_date']]
        else:
            # Get all stock items with location data
            stock_items = StockItem.get_all_with_locations()
        
        # Get products and bins for filter dropdowns
        products = Product.get_all()
        bins = Bin.get_all()
        
        # Get warehouse name for the filter if warehouse_id is provided
        selected_warehouse_name = None
        if warehouse_id:
            from backend.models.warehouse import Warehouse
            warehouse = Warehouse.get_by_id(warehouse_id)
            if warehouse:
                selected_warehouse_name = warehouse.name
        
        return render_template('stock.html',
                             stock_items=stock_items,
                             products=products,
                             bins=bins,
                             selected_product=product_id,
                             selected_bin=bin_id,
                             selected_warehouse=warehouse_id,
                             selected_warehouse_name=selected_warehouse_name,
                             filter_type=filter_type)
                             
    except Exception as e:
        logger.error(f"Error loading stock page: {e}")
        flash('Error loading stock. Please try again.', 'error')
        return render_template('stock.html', stock_items=[], products=[], bins=[])


@stock_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_stock():
    """Add new stock page"""
    if request.method == 'POST':
        try:
            # Get form data
            product_id = request.form.get('product_id', '').strip()
            bin_id = request.form.get('bin_id', '').strip()
            qty_available = int(request.form.get('qty_available', 0))
            qty_reserved = int(request.form.get('qty_reserved', 0))
            batch_id = request.form.get('batch_id', '').strip() or None
            expiry_date = request.form.get('expiry_date')
            expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d') if expiry_date else None
            
            # Validate required fields
            if not product_id or not bin_id or qty_available <= 0:
                flash('Please provide product, bin, and valid quantity.', 'error')
                return render_template('add_stock_modal.html')
            
            # Add stock using service
            result = StockService.handle_stock_receiving(
                product_id=product_id,
                bin_id=bin_id,
                qty_available=qty_available,
                qty_reserved=qty_reserved,
                batch_id=batch_id,
                expiry_date=expiry_date,
                user_id=current_user.id
            )
            
            if result:
                flash(f'Stock added successfully!', 'success')
                return redirect(url_for('stock.stock_list'))
            else:
                flash('Failed to add stock. Please try again.', 'error')
                
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            logger.error(f"Error adding stock: {e}")
            flash('An error occurred while adding stock.', 'error')
    
    # Get products and bins for dropdowns
    products = Product.get_all()
    bins = Bin.get_all()
    
    return render_template('add_stock_modal.html', products=products, bins=bins)


@stock_bp.route('/edit/<stock_id>', methods=['GET', 'POST'])
@login_required
def edit_stock(stock_id):
    """Edit stock page"""
    try:
        stock_item = StockItem.get_by_id(stock_id)
        if not stock_item:
            flash('Stock item not found.', 'error')
            return redirect(url_for('stock.stock_list'))
        
        if request.method == 'POST':
            # Get form data
            qty_available = int(request.form.get('qty_available', 0))
            qty_reserved = int(request.form.get('qty_reserved', 0))
            batch_id = request.form.get('batch_id', '').strip() or None
            expiry_date = request.form.get('expiry_date')
            expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d') if expiry_date else None
            
            # Update stock using service
            success = stock_item.update_stock(
                on_hand=qty_available,
                qty_reserved=qty_reserved
            )
            
            if success:
                # Update batch and expiry if provided
                if batch_id != stock_item.batch_id or expiry_date != stock_item.expiry_date:
                    stock_item.update(batch_id=batch_id, expiry_date=expiry_date)
                
                flash(f'Stock updated successfully!', 'success')
                return redirect(url_for('stock.stock_list'))
            else:
                flash('Failed to update stock. Please try again.', 'error')
        
        # Get products and bins for dropdowns
        products = Product.get_all()
        bins = Bin.get_all()
        
        return render_template('edit_stock_modal.html',
                             stock_item=stock_item,
                             products=products,
                             bins=bins)
                             
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('stock.stock_list'))
    except Exception as e:
        logger.error(f"Error editing stock {stock_id}: {e}")
        flash('An error occurred while editing the stock.', 'error')
        return redirect(url_for('stock.stock_list'))


@stock_bp.route('/delete/<stock_id>', methods=['POST'])
@login_required
def delete_stock(stock_id):
    """Delete stock item"""
    try:
        stock_item = StockItem.get_by_id(stock_id)
        if not stock_item:
            flash('Stock item not found.', 'error')
            return redirect(url_for('stock.stock_list'))
        
        # Delete stock item
        success = stock_item.delete()
        
        if success:
            flash(f'Stock item deleted successfully!', 'success')
        else:
            flash('Failed to delete stock item. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error deleting stock {stock_id}: {e}")
        flash('An error occurred while deleting the stock item.', 'error')
    
    return redirect(url_for('stock.stock_list'))


@stock_bp.route('/move/<stock_id>', methods=['GET', 'POST'])
@login_required
def move_stock(stock_id):
    """Move stock between bins"""
    try:
        stock_item = StockItem.get_by_id(stock_id)
        if not stock_item:
            flash('Stock item not found.', 'error')
            return redirect(url_for('stock.stock_list'))
        
        if request.method == 'POST':
            # Get form data
            dest_bin_id = request.form.get('dest_bin_id', '').strip()
            quantity = int(request.form.get('quantity', 0))
            notes = request.form.get('notes', '').strip()
            
            # Validate inputs
            if not dest_bin_id or quantity <= 0:
                flash('Please provide destination bin and valid quantity.', 'error')
                return render_template('move_stock_modal.html', stock_item=stock_item)
            
            if quantity > stock_item.available_stock:
                flash(f'Insufficient stock. Available: {stock_item.available_stock}', 'error')
                return render_template('move_stock_modal.html', stock_item=stock_item)
            
            # Move stock using service
            result = StockService.move_stock(
                source_stock_id=stock_id,
                dest_bin_id=dest_bin_id,
                quantity=quantity,
                user_id=current_user.id,
                notes=notes
            )
            
            if result and result.get('success'):
                flash(f'Stock moved successfully!', 'success')
                return redirect(url_for('stock.stock_list'))
            else:
                flash('Failed to move stock. Please try again.', 'error')
        
        # Get available bins for dropdown
        bins = Bin.get_all()
        
        return render_template('move_stock_modal.html',
                             stock_item=stock_item,
                             bins=bins)
                             
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('stock.stock_list'))
    except Exception as e:
        logger.error(f"Error moving stock {stock_id}: {e}")
        flash('An error occurred while moving the stock.', 'error')
        return redirect(url_for('stock.stock_list'))


@stock_bp.route('/details/<stock_id>')
@login_required
def stock_details(stock_id):
    """Stock details page"""
    try:
        stock_item = StockItem.get_by_id(stock_id)
        if not stock_item:
            flash('Stock item not found.', 'error')
            return redirect(url_for('stock.stock_list'))
        
        # Get related data
        product = Product.get_by_id(stock_item.product_id)
        bin_obj = Bin.get_by_id(stock_item.bin_id)
        transactions = StockTransaction.get_by_stock_item(stock_id)
        
        return render_template('stock_details_modal.html',
                             stock_item=stock_item,
                             product=product,
                             bin_obj=bin_obj,
                             transactions=transactions)
        
    except Exception as e:
        logger.error(f"Error loading stock details for {stock_id}: {e}")
        flash('Error loading stock details.', 'error')
        return redirect(url_for('stock.stock_list'))


# API Routes for Stock
@stock_bp.route('/api/list')
@login_required
def api_stock_list():
    """API endpoint for stock list"""
    try:
        product_id = request.args.get('product_id', '')
        bin_id = request.args.get('bin_id', '')
        limit = request.args.get('limit', 50, type=int)
        
        if product_id:
            stock_items = StockItem.get_by_product(product_id)
        elif bin_id:
            stock_items = StockItem.get_by_bin(bin_id)
        else:
            stock_items = StockItem.get_all()
        
        stock_items = stock_items[:limit]  # Apply limit
        
        stock_data = []
        for item in stock_items:
            product = Product.get_by_id(item.product_id)
            bin_obj = Bin.get_by_id(item.bin_id)
            
            stock_data.append({
                'id': item.id,
                'product': product.to_dict() if product else None,
                'bin': bin_obj.to_dict() if bin_obj else None,
                'on_hand': item.on_hand,
                'qty_reserved': item.qty_reserved,
                'available_stock': item.available_stock,
                'batch_id': item.batch_id,
                'expiry_date': item.expiry_date.isoformat() if item.expiry_date else None,
                'days_until_expiry': item.days_until_expiry(),
                'is_expired': item.is_expired()
            })
        
        return jsonify({
            'success': True,
            'stock_items': stock_data,
            'total': len(stock_data)
        })
        
    except Exception as e:
        logger.error(f"Error in stock API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load stock items'
        }), 500


@stock_bp.route('/api/<stock_id>')
@login_required
def api_stock_details(stock_id):
    """API endpoint for stock details"""
    try:
        stock_item = StockItem.get_by_id(stock_id)
        if not stock_item:
            return jsonify({
                'success': False,
                'error': 'Stock item not found'
            }), 404
        
        product = Product.get_by_id(stock_item.product_id)
        bin_obj = Bin.get_by_id(stock_item.bin_id)
        transactions = StockTransaction.get_by_stock_item(stock_id)
        
        return jsonify({
            'success': True,
            'stock_item': {
                'id': stock_item.id,
                'product': product.to_dict() if product else None,
                'bin': bin_obj.to_dict() if bin_obj else None,
                'on_hand': stock_item.on_hand,
                'qty_reserved': stock_item.qty_reserved,
                'available_stock': stock_item.available_stock,
                'batch_id': stock_item.batch_id,
                'expiry_date': stock_item.expiry_date.isoformat() if stock_item.expiry_date else None,
                'days_until_expiry': stock_item.days_until_expiry(),
                'is_expired': stock_item.is_expired()
            },
            'transactions': [t.to_dict() for t in transactions]
        })
        
    except Exception as e:
        logger.error(f"Error in stock details API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load stock details'
        }), 500


@stock_bp.route('/api/add', methods=['POST'])
@login_required
def api_add_stock():
    """API endpoint for adding stock"""
    try:
        data = request.get_json()
        
        result = StockService.handle_stock_receiving(
            product_id=data.get('product_id', ''),
            bin_id=data.get('bin_id', ''),
            qty_available=data.get('qty_available', 0),
            qty_reserved=data.get('qty_reserved', 0),
            batch_id=data.get('batch_id'),
            expiry_date=data.get('expiry_date'),
            user_id=current_user.id
        )
        
        if result:
            return jsonify({
                'success': True,
                'result': result,
                'message': 'Stock added successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add stock'
            }), 400
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error in add stock API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to add stock'
        }), 500


@stock_bp.route('/api/<stock_id>/move', methods=['POST'])
@login_required
def api_move_stock(stock_id):
    """API endpoint for moving stock"""
    try:
        data = request.get_json()
        
        result = StockService.move_stock(
            source_stock_id=stock_id,
            dest_bin_id=data.get('dest_bin_id', ''),
            quantity=data.get('quantity', 0),
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
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error in move stock API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to move stock'
        }), 500


@stock_bp.route('/api/summary')
@login_required
def api_stock_summary():
    """API endpoint for stock summary"""
    try:
        product_id = request.args.get('product_id')
        summary = StockService.get_stock_summary(product_id)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error in stock summary API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load stock summary'
        }), 500


@stock_bp.route('/api/transactions/<stock_id>')
@login_required
def api_stock_transactions(stock_id):
    """API endpoint for stock transactions"""
    try:
        transactions = StockTransaction.get_by_stock_item(stock_id)
        
        return jsonify({
            'success': True,
            'transactions': [t.to_dict() for t in transactions]
        })
        
    except Exception as e:
        logger.error(f"Error in stock transactions API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load stock transactions'
        }), 500


# Import datetime for date handling
from datetime import datetime
