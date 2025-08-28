"""
Route handlers for Inventory Management System
"""

from .auth import auth_bp
from .dashboard import dashboard_bp
from .products import products_bp
from .stock import stock_bp
from .warehouses import warehouses_bp
from .scanner import scanner_bp

__all__ = ['auth_bp', 'dashboard_bp', 'products_bp', 'stock_bp', 'warehouses_bp', 'scanner_bp']
