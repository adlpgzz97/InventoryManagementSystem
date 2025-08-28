"""
Dashboard Routes for Inventory Management System
Handles main dashboard, overview, and home page routes
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
import logging

from services.stock_service import StockService
from services.product_service import ProductService
from models.product import Product
from models.stock import StockItem
from models.warehouse import Warehouse

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page"""
    try:
        # Get dashboard statistics
        stats = get_dashboard_stats()
        
        # Get recent activities (placeholder for now)
        recent_activities = get_recent_activities()
        
        # Get alerts
        alerts = get_dashboard_alerts()
        
        return render_template('dashboard.html',
                             stats=stats,
                             recent_activities=recent_activities,
                             alerts=alerts)
                             
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('dashboard.html',
                             stats={},
                             recent_activities=[],
                             alerts=[],
                             error="Failed to load dashboard data")


@dashboard_bp.route('/api/stats')
@login_required
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    try:
        stats = get_dashboard_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
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
        alerts = get_dashboard_alerts()
        return jsonify({
            'success': True,
            'alerts': alerts
        })
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
        activities = get_recent_activities()
        return jsonify({
            'success': True,
            'activities': activities
        })
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
            'low_stock_count': 0,
            'overstocked_count': 0,
            'expiring_count': 0,
            'low_stock_percentage': 0,
            'overstocked_percentage': 0,
            'stock_utilization': 0
        }


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
        
        return render_template('admin_schema.html')
        
    except Exception as e:
        logger.error(f"Error loading admin schema: {e}")
        return render_template('error.html', 
                             message='Failed to load admin schema'), 500
