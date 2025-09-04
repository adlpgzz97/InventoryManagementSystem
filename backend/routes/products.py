"""
Products Routes for Inventory Management System
Handles product management pages and operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import logging

from backend.services.product_service import ProductService
from backend.models.product import Product
from backend.models.stock import StockItem

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
            products = ProductService.search_products(search_term)
        
        return render_template('products.html',
                             products=products,
                             search_term=search_term,
                             filter_type=filter_type)
                             
    except Exception as e:
        logger.error(f"Error loading products page: {e}")
        flash('Error loading products. Please try again.', 'error')
        return render_template('products.html', products=[])


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
            dimensions = request.form.get('dimensions', '').strip()
            weight = request.form.get('weight')
            weight = float(weight) if weight else None
            picture_url = request.form.get('picture_url', '').strip()
            batch_tracked = request.form.get('batch_tracked') == 'on'
            
            # Create product using service
            product = ProductService.create_product(
                name=name,
                description=description,
                sku=sku,
                barcode=barcode,
                dimensions=dimensions,
                weight=weight,
                picture_url=picture_url,
                batch_tracked=batch_tracked
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
    
    return render_template('add_product_modal.html')


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
            try:
                # Get form data
                name = request.form.get('name', '').strip()
                description = request.form.get('description', '').strip()
                sku = request.form.get('sku', '').strip()
                barcode = request.form.get('barcode', '').strip()
                dimensions = request.form.get('dimensions', '').strip()
                weight = request.form.get('weight')
                weight = float(weight) if weight else None
                picture_url = request.form.get('picture_url', '').strip()
                batch_tracked = request.form.get('batch_tracked') == 'on'
                
                # Update product using service
                success = ProductService.update_product(
                    product_id,
                    name=name,
                    description=description,
                    sku=sku,
                    barcode=barcode,
                    dimensions=dimensions,
                    weight=weight,
                    picture_url=picture_url,
                    batch_tracked=batch_tracked
                )
                
                if success:
                    flash(f'Product "{name}" updated successfully!', 'success')
                    return redirect(url_for('products.products_list'))
                else:
                    flash('Failed to update product. Please try again.', 'error')
                    
            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                logger.error(f"Error updating product: {e}")
                flash('An error occurred while updating the product.', 'error')
        
        return render_template('edit_product_modal.html', product=product)
        
    except Exception as e:
        logger.error(f"Error loading edit product page: {e}")
        flash('Error loading product details.', 'error')
        return redirect(url_for('products.products_list'))


@products_bp.route('/delete/<product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """Delete product"""
    try:
        success = ProductService.delete_product(product_id)
        
        if success:
            flash('Product deleted successfully!', 'success')
        else:
            flash('Failed to delete product. Please try again.', 'error')
            
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        logger.error(f"Error deleting product: {e}")
        flash('An error occurred while deleting the product.', 'error')
    
    return redirect(url_for('products.products_list'))


@products_bp.route('/api/search')
@login_required
def api_search_products():
    """API endpoint for product search"""
    try:
        search_term = request.args.get('q', '')
        products = ProductService.search_products(search_term)
        
        return jsonify({
            'success': True,
            'products': [product.to_dict() for product in products]
        })
        
    except Exception as e:
        logger.error(f"Error searching products: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to search products'
        }), 500


@products_bp.route('/api/<product_id>/details')
@login_required
def api_product_details(product_id):
    """API endpoint for product details"""
    logger.info(f"API product details called for product_id: {product_id}")
    logger.info(f"Product ID type: {type(product_id)}")
    logger.info(f"Product ID value: '{product_id}'")
    try:
        details = ProductService.get_product_details(product_id)
        
        if 'error' in details:
            return jsonify({
                'success': False,
                'error': details['error']
            }), 404
        
        return jsonify({
            'success': True,
            'details': details
        })
        
    except Exception as e:
        logger.error(f"Error getting product details: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get product details'
        }), 500


@products_bp.route('/details')
@login_required
def product_details_modal():
    """Serve product details modal template"""
    return render_template('product_details_modal.html')


@products_bp.route('/api/low-stock')
@login_required
def api_low_stock_products():
    """API endpoint for low stock products"""
    try:
        low_stock_products = ProductService.get_low_stock_products()
        
        return jsonify({
            'success': True,
            'products': low_stock_products
        })
        
    except Exception as e:
        logger.error(f"Error getting low stock products: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get low stock products'
        }), 500


@products_bp.route('/api/overstocked')
@login_required
def api_overstocked_products():
    """API endpoint for overstocked products"""
    try:
        overstocked_products = ProductService.get_overstocked_products()
        
        return jsonify({
            'success': True,
            'products': overstocked_products
        })
        
    except Exception as e:
        logger.error(f"Error getting overstocked products: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get overstocked products'
        }), 500


@products_bp.route('/api/expiring')
@login_required
def api_expiring_products():
    """API endpoint for expiring products"""
    try:
        days_threshold = int(request.args.get('days', 30))
        expiring_products = ProductService.get_expiring_products(days_threshold)
        
        return jsonify({
            'success': True,
            'products': expiring_products
        })
        
    except Exception as e:
        logger.error(f"Error getting expiring products: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get expiring products'
        }), 500


@products_bp.route('/api/debug/products')
@login_required
def api_debug_products():
    """Debug endpoint to list all products with their IDs"""
    try:
        products = Product.get_all()
        product_list = []
        for product in products:
            product_list.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku
            })
        
        return jsonify({
            'success': True,
            'products': product_list
        })
        
    except Exception as e:
        logger.error(f"Error getting debug products: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get debug products'
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
        logger.error(f"Error generating product report: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate product report'
        }), 500
