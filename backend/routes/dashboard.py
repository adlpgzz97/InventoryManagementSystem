"""
Dashboard Routes for Inventory Management System
Handles main dashboard, overview, and home page routes
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
import logging
from datetime import datetime, timedelta

from backend.services.dashboard_service import DashboardService
from backend.services.stock_service import StockService
from backend.services.product_service import ProductService
from backend.models.product import Product
from backend.models.stock import StockItem
from backend.models.warehouse import Warehouse

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page"""
    logger.info(f"Dashboard route accessed by user: {current_user.username}")
    
    try:
        # Use dashboard service to get data
        dashboard_service = DashboardService()
        dashboard_data = dashboard_service.get_user_dashboard_data(current_user.id)
        
        logger.info("Dashboard data loaded successfully via service, rendering template")
        return render_template('dashboard.html', **dashboard_data)
                             
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        
        # Return a simplified dashboard with error message
        return render_template('dashboard.html',
                             stats={},
                             alerts=[{
                                 'type': 'danger',
                                 'title': 'Dashboard Error',
                                 'message': f'Failed to load dashboard data: {str(e)}',
                                 'count': 1,
                                 'link': None
                             }],
                             stock_distribution={},
                             warehouse_distribution=[],
                             batch_analytics=None,
                             detailed_stock_report=[],
                             error="Failed to load dashboard data")


@dashboard_bp.route('/api/stats')
@login_required
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    try:
        dashboard_service = DashboardService()
        dashboard_data = dashboard_service.get_dashboard_data()
        return jsonify(dashboard_service.create_response(
            success=True,
            data=dashboard_data['stats'],
            message="Dashboard statistics loaded successfully"
        ))
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load dashboard statistics'
        }), 500


@dashboard_bp.route('/api/alerts')
@login_required
def api_dashboard_alerts():
    """API endpoint for dashboard alerts"""
    try:
        dashboard_service = DashboardService()
        dashboard_data = dashboard_service.get_dashboard_data()
        return jsonify(dashboard_service.create_response(
            success=True,
            data=dashboard_data['alerts'],
            message="Dashboard alerts loaded successfully"
        ))
    except Exception as e:
        logger.error(f"Error getting dashboard alerts: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load dashboard alerts'
        }), 500


@dashboard_bp.route('/api/recent-activities')
@login_required
def api_recent_activities():
    """API endpoint for recent activities"""
    try:
        dashboard_service = DashboardService()
        dashboard_data = dashboard_service.get_dashboard_data()
        return jsonify(dashboard_service.create_response(
            success=True,
            data=dashboard_data['recent_activity'],
            message="Recent activities loaded successfully"
        ))
    except Exception as e:
        logger.error(f"Error getting recent activities: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load recent activities'
        }), 500


def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        # Get basic counts
        products = Product.get_all()
        warehouses = Warehouse.get_all()
        
        # Get stock summary
        stock_summary = StockService.get_stock_summary()
        
        # Get low stock products
        low_stock_products = ProductService.get_low_stock_products()
        
        # Get overstocked products
        overstocked_products = ProductService.get_overstocked_products()
        
        # Get expiring products
        expiring_products = ProductService.get_expiring_products()
        
        # Calculate totals
        total_products = len(products)
        total_warehouses = len(warehouses)
        total_stock_items = stock_summary.get('total_stock_items', 0)
        total_on_hand = stock_summary.get('total_on_hand', 0)
        total_reserved = stock_summary.get('total_reserved', 0)
        total_available = stock_summary.get('total_available', 0)
        
        # Calculate inventory value (estimated) - placeholder for future implementation
        total_inventory_value = 0  # TODO: Add unit_price field to products table
        
        # Calculate percentages
        low_stock_count = len(low_stock_products)
        overstocked_count = len(overstocked_products)
        expiring_count = len(expiring_products)
        
        low_stock_percentage = (low_stock_count / total_products * 100) if total_products > 0 else 0
        overstocked_percentage = (overstocked_count / total_products * 100) if total_products > 0 else 0
        
        return {
            'total_products': total_products,
            'total_warehouses': total_warehouses,
            'total_stock_items': total_stock_items,
            'total_on_hand': total_on_hand,
            'total_reserved': total_reserved,
            'total_available': total_available,
            'total_inventory_value': total_inventory_value,
            'low_stock_count': low_stock_count,
            'overstocked_count': overstocked_count,
            'expiring_count': expiring_count,
            'low_stock_percentage': round(low_stock_percentage, 1),
            'overstocked_percentage': round(overstocked_percentage, 1),
            'stock_utilization': round((total_available / (total_on_hand + 1)) * 100, 1) if total_on_hand > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {
            'total_products': 0,
            'total_warehouses': 0,
            'total_stock_items': 0,
            'total_on_hand': 0,
            'total_reserved': 0,
            'total_available': 0,
            'total_inventory_value': 0,
            'low_stock_count': 0,
            'overstocked_count': 0,
            'expiring_count': 0,
            'low_stock_percentage': 0,
            'overstocked_percentage': 0,
            'stock_utilization': 0
        }


def get_stock_distribution():
    """Get stock level distribution"""
    try:
        stock_items = StockItem.get_all_with_locations()
        
        in_stock = 0
        low_stock = 0
        out_of_stock = 0
        
        for item in stock_items:
            available = item.get('available_stock', 0)
            if available == 0:
                out_of_stock += 1
            elif available <= 5:  # Low stock threshold
                low_stock += 1
            else:
                in_stock += 1
        
        return {
            'in_stock': in_stock,
            'low_stock': low_stock,
            'out_of_stock': out_of_stock
        }
        
    except Exception as e:
        logger.error(f"Error getting stock distribution: {e}")
        return {
            'in_stock': 0,
            'low_stock': 0,
            'out_of_stock': 0
        }


def get_warehouse_distribution():
    """Get inventory distribution by warehouse"""
    try:
        warehouses = Warehouse.get_all()
        distribution = []
        
        for warehouse in warehouses:
            bins = warehouse.get_bins()
            total_items = 0
            total_qty = 0
            
            for bin_obj in bins:
                stock_items = StockItem.get_by_bin(bin_obj.id)
                total_items += len(stock_items)
                total_qty += sum(item.on_hand for item in stock_items)
            
            distribution.append({
                'name': warehouse.name,
                'total_items': total_items,
                'total_qty': total_qty
            })
        
        return distribution
        
    except Exception as e:
        logger.error(f"Error getting warehouse distribution: {e}")
        return []


def get_batch_analytics():
    """Get batch tracking analytics"""
    try:
        stock_items = StockItem.get_all_with_locations()
        batch_items = [item for item in stock_items if item.get('batch_id')]
        
        if not batch_items:
            return None
        
        return StockService.analyze_batch_data(batch_items)
        
    except Exception as e:
        logger.error(f"Error getting batch analytics: {e}")
        return None


def get_detailed_stock_report():
    """Get detailed stock report for the table"""
    try:
        stock_items = StockItem.get_all_with_locations()
        detailed_report = []
        
        for item in stock_items:
            # Determine status
            available = item.get('available_stock', 0)
            if available == 0:
                status = 'out_of_stock'
            elif available <= 5:
                status = 'low_stock'
            else:
                status = 'in_stock'
            
            # Check if expiring soon (within 30 days)
            is_expiring_soon = False
            if item.get('expiry_date'):
                try:
                    expiry_date = item['expiry_date']
                    if isinstance(expiry_date, str):
                        expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                    days_to_expiry = (expiry_date - datetime.now().date()).days
                    is_expiring_soon = days_to_expiry <= 30 and days_to_expiry >= 0
                except:
                    pass
            
            detailed_report.append({
                'stock_id': item['id'],
                'product_name': item.get('product', {}).get('name', 'Unknown'),
                'sku': item.get('product', {}).get('sku', 'N/A'),
                'warehouse_name': item.get('warehouse', {}).get('name', 'Unknown'),
                'location': item.get('location', {}).get('code', 'Unknown'),
                'on_hand': item.get('on_hand', 0),
                'qty_reserved': item.get('qty_reserved', 0),
                'batch_id': item.get('batch_id'),
                'expiry_date': item.get('expiry_date'),
                'is_batch_tracked': bool(item.get('batch_id')),
                'is_expiring_soon': is_expiring_soon,
                'status': status
            })
        
        return detailed_report
        
    except Exception as e:
        logger.error(f"Error getting detailed stock report: {e}")
        return []


def get_dashboard_alerts():
    """Get dashboard alerts and warnings"""
    try:
        alerts = []
        
        # Low stock alerts
        low_stock_products = ProductService.get_low_stock_products()
        if low_stock_products:
            alerts.append({
                'type': 'warning',
                'title': 'Low Stock Alert',
                'message': f'{len(low_stock_products)} products are running low on stock',
                'count': len(low_stock_products),
                'link': '/products?filter=low_stock'
            })
        
        # Overstocked alerts
        overstocked_products = ProductService.get_overstocked_products()
        if overstocked_products:
            alerts.append({
                'type': 'info',
                'title': 'Overstocked Products',
                'message': f'{len(overstocked_products)} products are overstocked',
                'count': len(overstocked_products),
                'link': '/products?filter=overstocked'
            })
        
        # Expiring products alerts
        expiring_products = ProductService.get_expiring_products()
        if expiring_products:
            alerts.append({
                'type': 'danger',
                'title': 'Expiring Products',
                'message': f'{len(expiring_products)} products have items expiring soon',
                'count': len(expiring_products),
                'link': '/products?filter=expiring'
            })
        
        # Empty warehouses alert
        warehouses = Warehouse.get_all()
        empty_warehouses = []
        for warehouse in warehouses:
            bins = warehouse.get_bins()
            if not bins:
                empty_warehouses.append(warehouse)
        
        if empty_warehouses:
            alerts.append({
                'type': 'warning',
                'title': 'Empty Warehouses',
                'message': f'{len(empty_warehouses)} warehouses have no bins configured',
                'count': len(empty_warehouses),
                'link': '/warehouses'
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error getting dashboard alerts: {e}")
        return []


def get_recent_activities():
    """Get recent activities for dashboard"""
    try:
        # This would typically query transaction logs, user activities, etc.
        # For now, return a placeholder structure
        activities = [
            {
                'type': 'stock_received',
                'message': 'Stock received for Product XYZ',
                'timestamp': '2024-01-15 10:30:00',
                'user': 'admin'
            },
            {
                'type': 'stock_moved',
                'message': 'Stock moved from Bin A1 to Bin B2',
                'timestamp': '2024-01-15 09:15:00',
                'user': 'worker'
            },
            {
                'type': 'product_created',
                'message': 'New product "Widget Pro" created',
                'timestamp': '2024-01-14 16:45:00',
                'user': 'manager'
            }
        ]
        
        return activities
        
    except Exception as e:
        logger.error(f"Error getting recent activities: {e}")
        return []


@dashboard_bp.route('/admin/schema')
@login_required
def admin_schema():
    """Admin schema page"""
    try:
        # Check if user has admin permissions
        if not current_user.has_permission('manage_users'):
            return render_template('error.html', 
                                 message='Access denied. Admin privileges required.'), 403
        
        # Get database schema data
        schema_data = get_database_schema()
        
        return render_template('admin_schema.html', schema_data=schema_data)
        
    except Exception as e:
        logger.error(f"Error loading admin schema: {e}")
        return render_template('error.html', 
                             message='Failed to load admin schema'), 500


def get_database_schema():
    """Get database schema information"""
    try:
        # This is a simplified schema - in a real implementation, you'd query the database
        # to get actual schema information
        schema_data = {
            'users': {
                'row_count': 3,
                'columns': [
                    {'name': 'id', 'type': 'UUID', 'nullable': False, 'primary_key': True},
                    {'name': 'username', 'type': 'VARCHAR(50)', 'nullable': False},
                    {'name': 'role', 'type': 'VARCHAR(20)', 'nullable': False}
                ],
                'foreign_keys': []
            },
            'products': {
                'row_count': 5,
                'columns': [
                    {'name': 'id', 'type': 'UUID', 'nullable': False, 'primary_key': True},
                    {'name': 'name', 'type': 'VARCHAR(100)', 'nullable': False},
                    {'name': 'sku', 'type': 'VARCHAR(50)', 'nullable': True},
                    {'name': 'description', 'type': 'TEXT', 'nullable': True},
                    {'name': 'batch_tracked', 'type': 'BOOLEAN', 'nullable': False, 'default': False}
                ],
                'foreign_keys': []
            },
            'warehouses': {
                'row_count': 2,
                'columns': [
                    {'name': 'id', 'type': 'UUID', 'nullable': False, 'primary_key': True},
                    {'name': 'name', 'type': 'VARCHAR(100)', 'nullable': False},
                    {'name': 'code', 'type': 'VARCHAR(20)', 'nullable': False}
                ],
                'foreign_keys': []
            },
            'locations': {
                'row_count': 4,
                'columns': [
                    {'name': 'id', 'type': 'UUID', 'nullable': False, 'primary_key': True},
                    {'name': 'warehouse_id', 'type': 'UUID', 'nullable': False},
                    {'name': 'full_code', 'type': 'VARCHAR(50)', 'nullable': False}
                ],
                'foreign_keys': [
                    {'column': 'warehouse_id', 'references': 'warehouses(id)'}
                ]
            },
            'bins': {
                'row_count': 8,
                'columns': [
                    {'name': 'id', 'type': 'UUID', 'nullable': False, 'primary_key': True},
                    {'name': 'location_id', 'type': 'UUID', 'nullable': False},
                    {'name': 'code', 'type': 'VARCHAR(20)', 'nullable': False}
                ],
                'foreign_keys': [
                    {'column': 'location_id', 'references': 'locations(id)'}
                ]
            },
            'stock_items': {
                'row_count': 12,
                'columns': [
                    {'name': 'id', 'type': 'UUID', 'nullable': False, 'primary_key': True},
                    {'name': 'product_id', 'type': 'UUID', 'nullable': False},
                    {'name': 'bin_id', 'type': 'UUID', 'nullable': False},
                    {'name': 'on_hand', 'type': 'INTEGER', 'nullable': False, 'default': 0},
                    {'name': 'qty_reserved', 'type': 'INTEGER', 'nullable': False, 'default': 0},
                    {'name': 'batch_id', 'type': 'VARCHAR(50)', 'nullable': True},
                    {'name': 'expiry_date', 'type': 'DATE', 'nullable': True}
                ],
                'foreign_keys': [
                    {'column': 'product_id', 'references': 'products(id)'},
                    {'column': 'bin_id', 'references': 'bins(id)'}
                ]
            },
            'stock_transactions': {
                'row_count': 25,
                'columns': [
                    {'name': 'id', 'type': 'UUID', 'nullable': False, 'primary_key': True},
                    {'name': 'stock_item_id', 'type': 'UUID', 'nullable': False},
                    {'name': 'transaction_type', 'type': 'VARCHAR(20)', 'nullable': False},
                    {'name': 'quantity_change', 'type': 'INTEGER', 'nullable': False},
                    {'name': 'quantity_before', 'type': 'INTEGER', 'nullable': False},
                    {'name': 'quantity_after', 'type': 'INTEGER', 'nullable': False},
                    {'name': 'user_id', 'type': 'UUID', 'nullable': True}
                ],
                'foreign_keys': [
                    {'column': 'stock_item_id', 'references': 'stock_items(id)'},
                    {'column': 'user_id', 'references': 'users(id)'}
                ]
            }
        }
        
        return schema_data
        
    except Exception as e:
        logger.error(f"Error getting database schema: {e}")
        return {}
