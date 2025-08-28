"""
Products Routes for Inventory Management System
Handles product management pages and operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import logging

from services.product_service import ProductService
from models.product import Product
from models.stock import StockItem

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
products_bp = Blueprint('products', __name__, url_prefix='/products')


@products_bp.route('/')
@login_required
def products_list():
    """Products listing page"""
    try:
        # Get filter parameters
        search_term = request.args.get('search', '')
        category = request.args.get('category', '')
        filter_type = request.args.get('filter', '')
        
        # Get products based on filters
        if filter_type == 'low_stock':
            products_data = ProductService.get_low_stock_products()
            products = [Product.get_by_id(item['product']['id']) for item in products_data]
        elif filter_type == 'overstocked':
            products_data = ProductService.get_overstocked_products()
            products = [Product.get_by_id(item['product']['id']) for item in products_data]
        elif filter_type == 'expiring':
            products_data = ProductService.get_expiring_products()
            products = [Product.get_by_id(item['product']['id']) for item in products_data]
        else:
            products = ProductService.search_products(search_term, category)
        
        # Get categories for filter dropdown
        categories = ProductService.get_product_categories()
        
        return render_template('products.html',
                             products=products,
                             categories=categories,
                             search_term=search_term,
                             selected_category=category,
                             filter_type=filter_type)
                             
    except Exception as e:
        logger.error(f"Error loading products page: {e}")
        flash('Error loading products. Please try again.', 'error')
        return render_template('products.html', products=[], categories=[])


@products_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    """Add new product page"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            sku = request.form.get('sku', '').strip()
            barcode = request.form.get('barcode', '').strip()
            category = request.form.get('category', '').strip()
            unit = request.form.get('unit', '').strip()
            batch_tracked = request.form.get('batch_tracked') == 'on'
            min_stock_level = int(request.form.get('min_stock_level', 0))
            max_stock_level = request.form.get('max_stock_level')
            max_stock_level = int(max_stock_level) if max_stock_level else None
            
            # Create product using service
            product = ProductService.create_product(
                name=name,
                description=description,
                sku=sku,
                barcode=barcode,
                category=category,
                unit=unit,
                batch_tracked=batch_tracked,
                min_stock_level=min_stock_level,
                max_stock_level=max_stock_level
            )
            
            if product:
                flash(f'Product "{name}" created successfully!', 'success')
                return redirect(url_for('products.products_list'))
            else:
                flash('Failed to create product. Please try again.', 'error')
                
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            flash('An error occurred while creating the product.', 'error')
    
    # Get categories for dropdown
    categories = ProductService.get_product_categories()
    
    return render_template('add_product_modal.html', categories=categories)


@products_bp.route('/edit/<product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Edit product page"""
    try:
        product = Product.get_by_id(product_id)
        if not product:
            flash('Product not found.', 'error')
            return redirect(url_for('products.products_list'))
        
        if request.method == 'POST':
            # Get form data
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            sku = request.form.get('sku', '').strip()
            barcode = request.form.get('barcode', '').strip()
            category = request.form.get('category', '').strip()
            unit = request.form.get('unit', '').strip()
            batch_tracked = request.form.get('batch_tracked') == 'on'
            min_stock_level = int(request.form.get('min_stock_level', 0))
            max_stock_level = request.form.get('max_stock_level')
            max_stock_level = int(max_stock_level) if max_stock_level else None
            
            # Update product using service
            success = ProductService.update_product(
                product_id,
                name=name,
                description=description,
                sku=sku,
                barcode=barcode,
                category=category,
                unit=unit,
                batch_tracked=batch_tracked,
                min_stock_level=min_stock_level,
                max_stock_level=max_stock_level
            )
            
            if success:
                flash(f'Product "{name}" updated successfully!', 'success')
                return redirect(url_for('products.products_list'))
            else:
                flash('Failed to update product. Please try again.', 'error')
                
        # Get categories for dropdown
        categories = ProductService.get_product_categories()
        
        return render_template('edit_product_modal.html',
                             product=product,
                             categories=categories)
                             
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('products.products_list'))
    except Exception as e:
        logger.error(f"Error editing product {product_id}: {e}")
        flash('An error occurred while editing the product.', 'error')
        return redirect(url_for('products.products_list'))


@products_bp.route('/delete/<product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """Delete product"""
    try:
        product = Product.get_by_id(product_id)
        if not product:
            flash('Product not found.', 'error')
            return redirect(url_for('products.products_list'))
        
        # Delete product using service
        success = ProductService.delete_product(product_id)
        
        if success:
            flash(f'Product "{product.name}" deleted successfully!', 'success')
        else:
            flash('Failed to delete product. Please try again.', 'error')
            
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {e}")
        flash('An error occurred while deleting the product.', 'error')
    
    return redirect(url_for('products.products_list'))


@products_bp.route('/details/<product_id>')
@login_required
def product_details(product_id):
    """Product details page"""
    try:
        # Get comprehensive product details using service
        details = ProductService.get_product_details(product_id)
        
        if 'error' in details:
            flash(details['error'], 'error')
            return redirect(url_for('products.products_list'))
        
        return render_template('product_details_modal.html', details=details)
        
    except Exception as e:
        logger.error(f"Error loading product details for {product_id}: {e}")
        flash('Error loading product details.', 'error')
        return redirect(url_for('products.products_list'))


# API Routes for Products
@products_bp.route('/api/list')
@login_required
def api_products_list():
    """API endpoint for products list"""
    try:
        search_term = request.args.get('search', '')
        category = request.args.get('category', '')
        limit = request.args.get('limit', 50, type=int)
        
        products = ProductService.search_products(search_term, category)
        products = products[:limit]  # Apply limit
        
        products_data = [product.to_dict() for product in products]
        
        return jsonify({
            'success': True,
            'products': products_data,
            'total': len(products_data)
        })
        
    except Exception as e:
        logger.error(f"Error in products API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load products'
        }), 500


@products_bp.route('/api/<product_id>')
@login_required
def api_product_details(product_id):
    """API endpoint for product details"""
    try:
        details = ProductService.get_product_details(product_id)
        
        if 'error' in details:
            return jsonify({
                'success': False,
                'error': details['error']
            }), 404
        
        return jsonify({
            'success': True,
            'product': details
        })
        
    except Exception as e:
        logger.error(f"Error in product details API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load product details'
        }), 500


@products_bp.route('/api/create', methods=['POST'])
@login_required
def api_create_product():
    """API endpoint for creating product"""
    try:
        data = request.get_json()
        
        product = ProductService.create_product(
            name=data.get('name', ''),
            description=data.get('description'),
            sku=data.get('sku'),
            barcode=data.get('barcode'),
            category=data.get('category'),
            unit=data.get('unit'),
            batch_tracked=data.get('batch_tracked', False),
            min_stock_level=data.get('min_stock_level', 0),
            max_stock_level=data.get('max_stock_level')
        )
        
        if product:
            return jsonify({
                'success': True,
                'product': product.to_dict(),
                'message': 'Product created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create product'
            }), 400
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error in create product API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create product'
        }), 500


@products_bp.route('/api/<product_id>/update', methods=['PUT'])
@login_required
def api_update_product(product_id):
    """API endpoint for updating product"""
    try:
        data = request.get_json()
        
        success = ProductService.update_product(product_id, **data)
        
        if success:
            product = Product.get_by_id(product_id)
            return jsonify({
                'success': True,
                'product': product.to_dict(),
                'message': 'Product updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update product'
            }), 400
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error in update product API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update product'
        }), 500


@products_bp.route('/api/<product_id>/delete', methods=['DELETE'])
@login_required
def api_delete_product(product_id):
    """API endpoint for deleting product"""
    try:
        success = ProductService.delete_product(product_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Product deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete product'
            }), 400
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error in delete product API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete product'
        }), 500


@products_bp.route('/api/categories')
@login_required
def api_categories():
    """API endpoint for product categories"""
    try:
        categories = ProductService.get_product_categories()
        
        return jsonify({
            'success': True,
            'categories': categories
        })
        
    except Exception as e:
        logger.error(f"Error in categories API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load categories'
        }), 500


@products_bp.route('/api/report')
@login_required
def api_product_report():
    """API endpoint for product report"""
    try:
        report = ProductService.generate_product_report()
        
        if 'error' in report:
            return jsonify({
                'success': False,
                'error': report['error']
            }), 500
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"Error in product report API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate report'
        }), 500
