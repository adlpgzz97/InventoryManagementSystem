"""
Warehouses Routes for Inventory Management System
Handles warehouse management pages and operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import logging

from backend.models.warehouse import Warehouse, Location, Bin
from backend.models.stock import StockItem
from backend.utils.database import execute_query

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
        from backend.models.warehouse import Location, Bin
        if filter_type == 'empty':
            warehouses = Warehouse.get_all()
            empty_warehouses = []
            for w in warehouses:
                locations = Location.get_by_warehouse(w.id)
                w.locations = locations  # Add locations to warehouse object
                bins = []
                for location in locations:
                    bins.extend(Bin.get_by_location(location.id))
                if not bins:
                    empty_warehouses.append(w)
            warehouses = empty_warehouses
        elif filter_type == 'full':
            warehouses = Warehouse.get_all()
            # For now, skip full warehouse filter as utilization calculation is complex
            # Load location data for each warehouse
            for warehouse in warehouses:
                warehouse.locations = Location.get_by_warehouse(warehouse.id)
        else:
            warehouses = Warehouse.search(search_term) if search_term else Warehouse.get_all()
        
        # Load location data for each warehouse to support template rendering
        for warehouse in warehouses:
            warehouse.locations = Location.get_by_warehouse(warehouse.id)
        
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
        from backend.models.warehouse import Location, Bin
        locations = Location.get_by_warehouse(warehouse.id)
        bins = []
        for location in locations:
            bins.extend(Bin.get_by_location(location.id))
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
        from backend.models.warehouse import Location, Bin
        locations = Location.get_by_warehouse(warehouse_id)
        bins = []  # Will be populated from locations
        for location in locations:
            bins.extend(Bin.get_by_location(location.id))
        utilization = 0  # Calculate utilization if needed
        
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
        
        from backend.models.warehouse import Location
        locations = Location.get_by_warehouse(warehouse_id)
        
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
        
        from backend.models.warehouse import Location, Bin
        locations = Location.get_by_warehouse(warehouse.id)
        bins = []
        for location in locations:
            bins.extend(Bin.get_by_location(location.id))
        
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
            from backend.models.warehouse import Location, Bin
            locations = Location.get_by_warehouse(warehouse.id)
            bins = []
            for location in locations:
                bins.extend(Bin.get_by_location(location.id))
            utilization = 0  # Calculate utilization if needed
            
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
        
        from backend.models.warehouse import Location
        locations = Location.get_by_warehouse(warehouse_id)
        from backend.models.warehouse import Location, Bin
        locations = Location.get_by_warehouse(warehouse.id)
        bins = []
        for location in locations:
            bins.extend(Bin.get_by_location(location.id))
        utilization = 0  # Calculate utilization if needed
        
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
        from backend.models.warehouse import Location, Bin
        locations = Location.get_by_warehouse(warehouse.id)
        bins = []
        for location in locations:
            bins.extend(Bin.get_by_location(location.id))
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
        
        from backend.models.warehouse import Location
        locations = Location.get_by_warehouse(warehouse_id)
        
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
        
        from backend.models.warehouse import Location, Bin
        locations = Location.get_by_warehouse(warehouse.id)
        bins = []
        for location in locations:
            bins.extend(Bin.get_by_location(location.id))
        
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


@warehouses_bp.route('/api/bin/<bin_code>')
@login_required
def get_bin_details(bin_code):
    """Get detailed information about a bin including stock items"""
    try:
        # Get bin by code
        bin_obj = Bin.get_by_code(bin_code)
        if not bin_obj:
            return jsonify({'error': 'Bin not found'}), 404
        
        # Get warehouse information
        warehouse = bin_obj.get_warehouse()
        
        # Get location information
        location_code = None
        if bin_obj.location_id:
            location_result = execute_query(
                "SELECT full_code FROM locations WHERE id = %s",
                (bin_obj.location_id,),
                fetch_one=True
            )
            if location_result:
                location_code = location_result['full_code']
        
        # Get stock items in this bin
        stock_items = StockItem.get_by_bin(bin_obj.id)
        
        # Format stock items data
        formatted_stock_items = []
        for item in stock_items:
            # Get product information
            from backend.models.product import Product
            product = Product.get_by_id(item.product_id)
            
            formatted_stock_items.append({
                'id': item.id,
                'product_name': product.name if product else 'Unknown Product',
                'sku': product.sku if product else 'N/A',
                'barcode': product.barcode if product else None,
                'on_hand': item.on_hand,
                'qty_reserved': item.qty_reserved,
                'total_qty': item.on_hand + item.qty_reserved,
                'batch_id': item.batch_id,
                'expiry_date': item.expiry_date.isoformat() if item.expiry_date else None
            })
        
        # Check if bin actually has stock (items with quantity > 0)
        has_actual_stock = any(item.on_hand > 0 for item in stock_items)
        
        # Format bin data
        bin_data = {
            'id': bin_obj.id,
            'code': bin_obj.code,
            'location_code': location_code,
            'warehouse_id': warehouse.id if warehouse else None,
            'warehouse_name': warehouse.name if warehouse else None,
            'warehouse_code': warehouse.code if warehouse else None,
            'warehouse_address': warehouse.address if warehouse else None,
            'has_stock': has_actual_stock,
            'stock_items': formatted_stock_items
        }
        
        return jsonify({
            'bin': bin_data,
            'stock_items': formatted_stock_items
        })
        
    except Exception as e:
        logger.error(f"Error getting bin details: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to get bin details: {str(e)}'}), 500


@warehouses_bp.route('/api/bin/<bin_code>/change-location', methods=['POST'])
@login_required
def change_bin_location(bin_code):
    """Change the location of a bin"""
    try:
        data = request.get_json()
        new_location_code = data.get('new_location_code')
        notes = data.get('notes', '')
        
        if not new_location_code:
            return jsonify({'error': 'New location code is required'}), 400
        
        # Get the bin
        bin_obj = Bin.get_by_code(bin_code)
        if not bin_obj:
            return jsonify({'error': 'Bin not found'}), 404
        
        # Get the new location
        from utils.database import execute_query
        location_result = execute_query(
            "SELECT id, full_code FROM locations WHERE full_code = %s",
            (new_location_code,),
            fetch_one=True
        )
        
        if not location_result:
            return jsonify({'error': 'Location not found'}), 404
        
        # Update the bin's location
        update_result = execute_query(
            "UPDATE bins SET location_id = %s WHERE id = %s RETURNING id",
            (location_result['id'], bin_obj.id),
            fetch_one=True
        )
        
        if update_result:
            return jsonify({
                'success': True,
                'message': f'Bin {bin_code} location changed to {new_location_code}',
                'bin_code': bin_code,
                'new_location_code': new_location_code
            })
        else:
            return jsonify({'error': 'Failed to update bin location'}), 500
            
    except Exception as e:
        logger.error(f"Error changing bin location: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to change bin location: {str(e)}'}), 500


@warehouses_bp.route('/api/locations/search')
@login_required
def search_locations():
    """Search for locations by code or name"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'success': True,
                'locations': []
            })
        
        from utils.database import execute_query
        locations = execute_query(
            """
            SELECT id, full_code, name, description, warehouse_id
            FROM locations 
            WHERE full_code ILIKE %s OR name ILIKE %s
            ORDER BY full_code
            LIMIT 20
            """,
            (f'%{query}%', f'%{query}%'),
            fetch_all=True
        )
        
        return jsonify({
            'success': True,
            'locations': locations
        })
        
    except Exception as e:
        logger.error(f"Error searching locations: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to search locations'
        }), 500


@warehouses_bp.route('/api/rack/delete', methods=['POST'])
@login_required
def delete_rack():
    """Delete a rack and all its associated locations and bins"""
    try:
        data = request.get_json()
        area_code = data.get('area_code')
        rack_code = data.get('rack_code')
        
        if not area_code or not rack_code:
            return jsonify({'error': 'Area code and rack code are required'}), 400
        
        # Get the warehouse ID from the current request context
        # We need to find locations that match the rack pattern
        from utils.database import execute_query
        
        # Find all locations that belong to this rack
        # The pattern is: {warehouse_code}{area_number}{rack_letter}{level_number}
        # We need to find locations where the rack letter matches
        rack_letter = rack_code[1:]  # Remove 'R' prefix from rack_code (e.g., R01 -> 01)
        
        # Convert rack number back to letter (R01 -> A, R02 -> B, etc.)
        try:
            rack_number = int(rack_letter)
            rack_letter_char = chr(ord('A') + rack_number - 1)
        except (ValueError, OverflowError):
            return jsonify({'error': 'Invalid rack code format'}), 400
        
        # Find locations that match this rack pattern
        # Pattern: {warehouse_code}{area_number}{rack_letter}{level_number}
        area_number = area_code[1:]  # Remove 'A' prefix (e.g., A1 -> 1)
        
        # Build the pattern to match locations
        # We need to find all locations that start with the warehouse code + area + rack letter
        pattern = f'%{area_number}{rack_letter_char}%'
        
        locations_result = execute_query(
            """
            SELECT id, full_code, warehouse_id
            FROM locations 
            WHERE full_code LIKE %s
            """,
            (pattern,),
            fetch_all=True
        )
        
        if not locations_result:
            return jsonify({'error': 'No locations found for this rack'}), 404
        
        # Check if any of these locations have bins
        location_ids = [loc['id'] for loc in locations_result]
        
        # Check for any bins in these locations
        bins_check = execute_query(
            """
            SELECT COUNT(*) as bin_count
            FROM bins 
            WHERE location_id = ANY(%s::uuid[])
            """,
            (location_ids,),
            fetch_one=True
        )
        
        if bins_check and bins_check['bin_count'] > 0:
            return jsonify({
                'error': f'Cannot delete rack: {bins_check["bin_count"]} bins are still associated with this rack'
            }), 400
        
        # Delete all locations in this rack (no bins to delete since we confirmed there are none)
        deleted_locations = execute_query(
            """
            DELETE FROM locations 
            WHERE id = ANY(%s::uuid[])
            RETURNING id, full_code
            """,
            (location_ids,),
            fetch_all=True
        )
        
        if deleted_locations:
            return jsonify({
                'success': True,
                'message': f'Rack {rack_code} deleted successfully',
                'deleted_locations': len(deleted_locations),
                'locations': [loc['full_code'] for loc in deleted_locations]
            })
        else:
            return jsonify({'error': 'No locations were deleted'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting rack: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to delete rack: {str(e)}'}), 500