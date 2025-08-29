"""
Warehouses Routes for Inventory Management System
Handles warehouse management pages and operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import logging

from models.warehouse import Warehouse, Location, Bin
from models.stock import StockItem

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
warehouses_bp = Blueprint('warehouses', __name__, url_prefix='/warehouses')


@warehouses_bp.route('/')
@login_required
def warehouses_list():
    """Warehouses listing page"""
    try:
        # Get filter parameters
        search_term = request.args.get('search', '')
        filter_type = request.args.get('filter', '')
        
        # Get warehouses based on filters
        if filter_type == 'empty':
            warehouses = Warehouse.get_all()
            warehouses = [w for w in warehouses if not w.get_bins()]
        elif filter_type == 'full':
            warehouses = Warehouse.get_all()
            warehouses = [w for w in warehouses if w.get_utilization_percentage() > 80]
        else:
            warehouses = Warehouse.search(search_term) if search_term else Warehouse.get_all()
        
        return render_template('warehouses.html',
                             warehouses=warehouses,
                             search_term=search_term,
                             filter_type=filter_type)
                             
    except Exception as e:
        logger.error(f"Error loading warehouses page: {e}")
        flash('Error loading warehouses. Please try again.', 'error')
        return render_template('warehouses.html', warehouses=[])


@warehouses_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_warehouse():
    """Add new warehouse page"""
    # Check if this is a modal request
    is_modal = request.args.get('modal') == '1'
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            address = request.form.get('address', '').strip()
            code = request.form.get('code', '').strip()
            
            # Validate required fields
            if not name:
                flash('Warehouse name is required.', 'error')
                return render_template('add_warehouse_modal.html')
            
            # Create warehouse
            warehouse = Warehouse.create(
                name=name,
                address=address,
                code=code
            )
            
            if warehouse:
                flash(f'Warehouse "{name}" created successfully!', 'success')
                if is_modal:
                    return redirect(url_for('warehouses.warehouses_list'))
                else:
                    return redirect(url_for('warehouses.warehouses_list'))
            else:
                flash('Failed to create warehouse. Please try again.', 'error')
                
        except Exception as e:
            logger.error(f"Error creating warehouse: {e}")
            flash('An error occurred while creating the warehouse.', 'error')
    
    return render_template('add_warehouse_modal.html')


@warehouses_bp.route('/edit/<warehouse_id>', methods=['GET', 'POST'])
@login_required
def edit_warehouse(warehouse_id):
    """Edit warehouse page"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            flash('Warehouse not found.', 'error')
            return redirect(url_for('warehouses.warehouses_list'))
        
        # Check if this is a modal request
        is_modal = request.args.get('modal') == '1'
        
        if request.method == 'POST':
            # Get form data
            name = request.form.get('name', '').strip()
            address = request.form.get('address', '').strip()
            code = request.form.get('code', '').strip()
            
            # Validate required fields
            if not name:
                flash('Warehouse name is required.', 'error')
                return render_template('edit_warehouse_modal.html', warehouse=warehouse)
            
            # Update warehouse
            success = warehouse.update(
                name=name,
                address=address,
                code=code
            )
            
            if success:
                flash(f'Warehouse "{name}" updated successfully!', 'success')
                if is_modal:
                    return redirect(url_for('warehouses.warehouses_list'))
                else:
                    return redirect(url_for('warehouses.warehouses_list'))
            else:
                flash('Failed to update warehouse. Please try again.', 'error')
        
        return render_template('edit_warehouse_modal.html', warehouse=warehouse)
                             
    except Exception as e:
        logger.error(f"Error editing warehouse {warehouse_id}: {e}")
        flash('An error occurred while editing the warehouse.', 'error')
        return redirect(url_for('warehouses.warehouses_list'))


@warehouses_bp.route('/delete/<warehouse_id>', methods=['POST'])
@login_required
def delete_warehouse(warehouse_id):
    """Delete warehouse"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            flash('Warehouse not found.', 'error')
            return redirect(url_for('warehouses.warehouses_list'))
        
        # Check if warehouse has bins with stock
        bins = warehouse.get_bins()
        for bin_obj in bins:
            stock_items = StockItem.get_by_bin(bin_obj.id)
            if stock_items:
                total_stock = sum(item.on_hand for item in stock_items)
                if total_stock > 0:
                    flash(f'Cannot delete warehouse with {total_stock} units in stock.', 'error')
                    return redirect(url_for('warehouses.warehouses_list'))
        
        # Delete warehouse
        success = warehouse.delete()
        
        if success:
            flash(f'Warehouse "{warehouse.name}" deleted successfully!', 'success')
        else:
            flash('Failed to delete warehouse. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error deleting warehouse {warehouse_id}: {e}")
        flash('An error occurred while deleting the warehouse.', 'error')
    
    return redirect(url_for('warehouses.warehouses_list'))


@warehouses_bp.route('/details/<warehouse_id>')
@login_required
def warehouse_details(warehouse_id):
    """Warehouse details page"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            flash('Warehouse not found.', 'error')
            return redirect(url_for('warehouses.warehouses_list'))
        
        # Get warehouse data
        locations = warehouse.get_locations()
        bins = warehouse.get_bins()
        utilization = warehouse.get_utilization_percentage()
        
        # Get stock summary for warehouse
        total_stock = 0
        total_bins_with_stock = 0
        for bin_obj in bins:
            stock_items = StockItem.get_by_bin(bin_obj.id)
            bin_stock = sum(item.on_hand for item in stock_items)
            total_stock += bin_stock
            if bin_stock > 0:
                total_bins_with_stock += 1
        
        return render_template('warehouse_details_modal.html',
                             warehouse=warehouse,
                             locations=locations,
                             bins=bins,
                             utilization=utilization,
                             total_stock=total_stock,
                             total_bins_with_stock=total_bins_with_stock)
        
    except Exception as e:
        logger.error(f"Error loading warehouse details for {warehouse_id}: {e}")
        flash('Error loading warehouse details.', 'error')
        return redirect(url_for('warehouses.warehouses_list'))


@warehouses_bp.route('/<warehouse_id>/locations')
@login_required
def warehouse_locations(warehouse_id):
    """Warehouse locations page"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            flash('Warehouse not found.', 'error')
            return redirect(url_for('warehouses.warehouses_list'))
        
        locations = warehouse.get_locations()
        
        return render_template('warehouse_locations.html',
                             warehouse=warehouse,
                             locations=locations)
        
    except Exception as e:
        logger.error(f"Error loading warehouse locations for {warehouse_id}: {e}")
        flash('Error loading warehouse locations.', 'error')
        return redirect(url_for('warehouses.warehouses_list'))


@warehouses_bp.route('/<warehouse_id>/hierarchy')
@login_required
def warehouse_hierarchy(warehouse_id):
    """Warehouse hierarchical view page"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            flash('Warehouse not found.', 'error')
            return redirect(url_for('warehouses.warehouses_list'))
        
        hierarchical_data = warehouse.get_hierarchical_locations()
        
        return render_template('warehouse_hierarchy.html',
                             warehouse=warehouse,
                             hierarchical_data=hierarchical_data)
        
    except Exception as e:
        logger.error(f"Error loading warehouse hierarchy for {warehouse_id}: {e}")
        flash('Error loading warehouse hierarchy.', 'error')
        return redirect(url_for('warehouses.warehouses_list'))


@warehouses_bp.route('/<warehouse_id>/bins')
@login_required
def warehouse_bins(warehouse_id):
    """Warehouse bins page"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            flash('Warehouse not found.', 'error')
            return redirect(url_for('warehouses.warehouses_list'))
        
        bins = warehouse.get_bins()
        
        # Get stock information for each bin
        for bin_obj in bins:
            stock_items = StockItem.get_by_bin(bin_obj.id)
            bin_obj.stock_count = len(stock_items)
            bin_obj.total_stock = sum(item.on_hand for item in stock_items)
        
        return render_template('warehouse_bins.html',
                             warehouse=warehouse,
                             bins=bins)
        
    except Exception as e:
        logger.error(f"Error loading warehouse bins for {warehouse_id}: {e}")
        flash('Error loading warehouse bins.', 'error')
        return redirect(url_for('warehouses.warehouses_list'))


# API Routes for Warehouses
@warehouses_bp.route('/api/list')
@login_required
def api_warehouses_list():
    """API endpoint for warehouses list"""
    try:
        search_term = request.args.get('search', '')
        limit = request.args.get('limit', 50, type=int)
        
        warehouses = Warehouse.search(search_term) if search_term else Warehouse.get_all()
        warehouses = warehouses[:limit]  # Apply limit
        
        warehouses_data = []
        for warehouse in warehouses:
            bins = warehouse.get_bins()
            utilization = warehouse.get_utilization_percentage()
            
            warehouses_data.append({
                'id': warehouse.id,
                'name': warehouse.name,
                'description': warehouse.description,
                'address': warehouse.address,
                'contact_person': warehouse.contact_person,
                'contact_email': warehouse.contact_email,
                'contact_phone': warehouse.contact_phone,
                'total_bins': len(bins),
                'utilization_percentage': utilization
            })
        
        return jsonify({
            'success': True,
            'warehouses': warehouses_data,
            'total': len(warehouses_data)
        })
        
    except Exception as e:
        logger.error(f"Error in warehouses API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load warehouses'
        }), 500


@warehouses_bp.route('/api/<warehouse_id>')
@login_required
def api_warehouse_details(warehouse_id):
    """API endpoint for warehouse details"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            return jsonify({
                'success': False,
                'error': 'Warehouse not found'
            }), 404
        
        locations = warehouse.get_locations()
        bins = warehouse.get_bins()
        utilization = warehouse.get_utilization_percentage()
        
        # Get stock summary
        total_stock = 0
        total_bins_with_stock = 0
        for bin_obj in bins:
            stock_items = StockItem.get_by_bin(bin_obj.id)
            bin_stock = sum(item.on_hand for item in stock_items)
            total_stock += bin_stock
            if bin_stock > 0:
                total_bins_with_stock += 1
        
        return jsonify({
            'success': True,
            'warehouse': {
                'id': warehouse.id,
                'name': warehouse.name,
                'description': warehouse.description,
                'address': warehouse.address,
                'contact_person': warehouse.contact_person,
                'contact_email': warehouse.contact_email,
                'contact_phone': warehouse.contact_phone,
                'total_locations': len(locations),
                'total_bins': len(bins),
                'utilization_percentage': utilization,
                'total_stock': total_stock,
                'total_bins_with_stock': total_bins_with_stock
            },
            'locations': [loc.to_dict() for loc in locations],
            'bins': [bin_obj.to_dict() for bin_obj in bins]
        })
        
    except Exception as e:
        logger.error(f"Error in warehouse details API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load warehouse details'
        }), 500


@warehouses_bp.route('/api/create', methods=['POST'])
@login_required
def api_create_warehouse():
    """API endpoint for creating warehouse"""
    try:
        data = request.get_json()
        
        warehouse = Warehouse.create(
            name=data.get('name', ''),
            description=data.get('description'),
            address=data.get('address'),
            contact_person=data.get('contact_person'),
            contact_email=data.get('contact_email'),
            contact_phone=data.get('contact_phone')
        )
        
        if warehouse:
            return jsonify({
                'success': True,
                'warehouse': warehouse.to_dict(),
                'message': 'Warehouse created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create warehouse'
            }), 400
            
    except Exception as e:
        logger.error(f"Error in create warehouse API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create warehouse'
        }), 500


@warehouses_bp.route('/api/<warehouse_id>/update', methods=['PUT'])
@login_required
def api_update_warehouse(warehouse_id):
    """API endpoint for updating warehouse"""
    try:
        data = request.get_json()
        
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            return jsonify({
                'success': False,
                'error': 'Warehouse not found'
            }), 404
        
        success = warehouse.update(**data)
        
        if success:
            return jsonify({
                'success': True,
                'warehouse': warehouse.to_dict(),
                'message': 'Warehouse updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update warehouse'
            }), 400
            
    except Exception as e:
        logger.error(f"Error in update warehouse API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update warehouse'
        }), 500


@warehouses_bp.route('/api/<warehouse_id>/delete', methods=['DELETE'])
@login_required
def api_delete_warehouse(warehouse_id):
    """API endpoint for deleting warehouse"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            return jsonify({
                'success': False,
                'error': 'Warehouse not found'
            }), 404
        
        # Check if warehouse has stock
        bins = warehouse.get_bins()
        for bin_obj in bins:
            stock_items = StockItem.get_by_bin(bin_obj.id)
            if stock_items:
                total_stock = sum(item.on_hand for item in stock_items)
                if total_stock > 0:
                    return jsonify({
                        'success': False,
                        'error': f'Cannot delete warehouse with {total_stock} units in stock'
                    }), 400
        
        success = warehouse.delete()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Warehouse deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete warehouse'
            }), 400
            
    except Exception as e:
        logger.error(f"Error in delete warehouse API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete warehouse'
        }), 500


@warehouses_bp.route('/api/<warehouse_id>/locations')
@login_required
def api_warehouse_locations(warehouse_id):
    """API endpoint for warehouse locations"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            return jsonify({
                'success': False,
                'error': 'Warehouse not found'
            }), 404
        
        locations = warehouse.get_locations()
        
        return jsonify({
            'success': True,
            'locations': [loc.to_dict() for loc in locations]
        })
        
    except Exception as e:
        logger.error(f"Error in warehouse locations API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load warehouse locations'
        }), 500


@warehouses_bp.route('/api/<warehouse_id>/bins')
@login_required
def api_warehouse_bins(warehouse_id):
    """API endpoint for warehouse bins"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            return jsonify({
                'success': False,
                'error': 'Warehouse not found'
            }), 404
        
        bins = warehouse.get_bins()
        
        # Add stock information to each bin
        bins_data = []
        for bin_obj in bins:
            stock_items = StockItem.get_by_bin(bin_obj.id)
            bin_data = bin_obj.to_dict()
            bin_data['stock_count'] = len(stock_items)
            bin_data['total_stock'] = sum(item.on_hand for item in stock_items)
            bins_data.append(bin_data)
        
        return jsonify({
            'success': True,
            'bins': bins_data
        })
        
    except Exception as e:
        logger.error(f"Error in warehouse bins API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load warehouse bins'
        }), 500


@warehouses_bp.route('/api/<warehouse_id>/hierarchy')
@login_required
def api_warehouse_hierarchy(warehouse_id):
    """API endpoint for warehouse hierarchical structure"""
    try:
        warehouse = Warehouse.get_by_id(warehouse_id)
        if not warehouse:
            return jsonify({
                'success': False,
                'error': 'Warehouse not found'
            }), 404
        
        hierarchical_data = warehouse.get_hierarchical_locations()
        
        return jsonify({
            'success': True,
            'warehouse': {
                'id': warehouse.id,
                'name': warehouse.name,
                'address': warehouse.address,
                'code': warehouse.code
            },
            'hierarchy': hierarchical_data
        })
        
    except Exception as e:
        logger.error(f"Error in warehouse hierarchy API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load warehouse hierarchy'
        }), 500
